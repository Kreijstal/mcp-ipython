import asyncio
import atexit
import queue # For queue.Empty exception
import time # Added for manual timeout management

from fastmcp import FastMCP, Context
from jupyter_client import KernelManager

class HistoryManager:
    def __init__(self):
        self.history_file = "ipython_auto_history.py"
        self._ensure_history_file()
    
    def _ensure_history_file(self):
        """Ensure history file exists with proper header"""
        try:
            with open(self.history_file, 'a+') as f:
                if f.tell() == 0:  # File is empty
                    f.write("# Automatic IPython Command History\n")
        except Exception as e:
            print(f"Warning: Could not initialize history file: {e}")

    def save_command(self, command):
        """Append a command to history file"""
        try:
            with open(self.history_file, 'a') as f:
                if not command.startswith(('get_ipython', '%')) and command.strip():
                    f.write(f"{command}\n")
        except Exception as e:
            print(f"Warning: Could not save command to history: {e}")

# Global kernel manager and client
km = None
kc = None

def start_ipython_kernel():
    """Starts and initializes the IPython kernel and client."""
    global km, kc
    if km and km.is_alive():
        print("IPython kernel already running.")
        return

    print("Starting IPython kernel...")
    km = KernelManager()
    km.start_kernel()
    print("IPython kernel process started.")
    
    kc = km.client()
    kc.start_channels()
    print("IPython kernel client channels started.")
    
    try:
        kc.wait_for_ready(timeout=30)
        print("IPython kernel client connected and ready.")
    except RuntimeError:
        print("Timeout waiting for IPython kernel to be ready.")
        shutdown_ipython_kernel()
        raise Exception("Failed to connect to IPython kernel in time.")

def shutdown_ipython_kernel():
    """Shuts down the IPython kernel and client."""
    global km, kc
    print("Attempting to shutdown IPython kernel...")
    if kc:
        if kc.channels_running:
            kc.stop_channels()
            print("IPython kernel client channels stopped.")
        kc = None
    
    if km:
        if km.is_alive():
            km.shutdown_kernel(now=True)
            print("IPython kernel shutdown signal sent.")
            try:
                km.wait(timeout=5)
                print("IPython kernel process terminated.")
            except TimeoutError:
                print("Timeout waiting for kernel process to terminate.")
        km = None
    print("IPython kernel shutdown process complete.")

mcp = FastMCP("IPython Backend MCP Server 🚀")

# SymPy Example Usage (uncomment to test):
#  1. Symbolic variables: `x, y = symbols('x y')`
#  2. Equation solving: `solve(x**2 - 5*x + 6, x)` → [2, 3]
#  3. Calculus: `diff(sin(x)*exp(x), x)` → exp(x)*sin(x) + exp(x)*cos(x)
#  4. Pretty printing: `init_printing()`
#  5. Matrices: `Matrix([[1, 2], [3, 4]])`

@mcp.tool()
async def send_command(command: str, ctx: Context) -> str:
    """
    Executes a Python command in the IPython kernel and returns its output.
    Output includes status, stdout, stderr, and execution results.
    """
    global kc, km
    if not kc or not km or not km.is_alive():
        await ctx.error("IPython kernel is not running or client not connected.")
        try:
            await ctx.info("Attempting to restart IPython kernel...")
            start_ipython_kernel()
            await ctx.info("IPython kernel restarted. Please try the command again.")
            return "Error: IPython kernel was not running. It has been restarted. Please try your command again."
        except Exception as e:
            await ctx.error(f"Failed to restart IPython kernel: {e}")
            return f"Error: IPython kernel not available and failed to restart: {e}"

    # Initialize history manager if not exists
    if not hasattr(send_command, '_history_manager'):
        send_command._history_manager = HistoryManager()
    
    # Save command to history before execution
    send_command._history_manager.save_command(command)
    
    await ctx.info(f"Executing command in IPython: {command}")
    
    if not kc.channels_running:
        await ctx.warn("Kernel client channels were not running. Restarting them.")
        kc.start_channels()
        try:
            await asyncio.to_thread(kc.wait_for_ready, timeout=10)
        except RuntimeError:
            await ctx.error("Failed to re-establish connection with kernel after channel restart.")
            return "Error: Failed to ensure kernel client readiness."

    msg_id = await asyncio.to_thread(kc.execute, command)
    outputs = []
    
    # IOPub Message Processing Loop
    iopub_timeout_duration = 10.0 # Overall timeout in seconds for IOPub messages for this command
    iopub_start_time = time.monotonic()
    
    await ctx.info(f"DEBUG: Starting IOPub message polling for msg_id: {msg_id} (overall timeout: {iopub_timeout_duration}s)")
    
    kernel_reported_idle_for_request = False

    while True:
        if time.monotonic() - iopub_start_time > iopub_timeout_duration:
            outputs.append("  (Overall timeout waiting for all IOPub messages or kernel to go idle for this request)")
            await ctx.info(f"DEBUG: Overall IOPub timeout for msg_id {msg_id} reached.")
            break

        try:
            # Poll with a short timeout.
            iopub_msg = await asyncio.to_thread(kc.get_iopub_msg, timeout=0.5) 

            if iopub_msg['parent_header'].get('msg_id') == msg_id:
                msg_type = iopub_msg['header']['msg_type']
                content = iopub_msg['content']
                await ctx.info(f"DEBUG: Received matching IOPub msg_type: {msg_type} for msg_id: {msg_id}")

                if msg_type == 'status':
                    exec_state = content['execution_state']
                    outputs.append(f"  Kernel Status: {exec_state}")
                    if exec_state == 'idle':
                        await ctx.info(f"DEBUG: Kernel reported idle for msg_id {msg_id}. Will continue polling until overall timeout for any trailing messages.")
                        kernel_reported_idle_for_request = True 
                        # We don't break here, to allow collection of trailing messages.
                elif msg_type == 'stream':
                    outputs.append(f"  {content['name'].capitalize()}: {content['text'].strip()}")
                elif msg_type == 'execute_result':
                    data = content.get('data', {})
                    text_plain = data.get('text/plain', '')
                    if text_plain:
                        outputs.append(f"  Result: {text_plain.strip()}")
                    else:
                        outputs.append(f"  Execute_Result (no text/plain, available data keys: {list(data.keys()) if data else 'data field missing or empty'})")
                elif msg_type == 'display_data':
                     outputs.append(f"  Display Data: {content['data'].get('text/plain', 'No plain text data').strip()}")
                elif msg_type == 'error': # This is an IOPub error message
                    outputs.append(f"  IOPub Error: {content.get('ename', 'N/A')} - {content.get('evalue', 'N/A')}")
                    tb = content.get('traceback', [])
                    if tb:
                        outputs.append("  IOPub Traceback:")
                        outputs.extend([f"    {line}" for line in tb])
            else:
                await ctx.info(f"DEBUG: Ignored IOPub msg_type: {iopub_msg['header']['msg_type']} for parent_id: {iopub_msg['parent_header'].get('msg_id')} (current msg_id: {msg_id})")
        
        except queue.Empty: 
            await ctx.info(f"DEBUG: queue.Empty on get_iopub_msg for msg_id {msg_id}. Continuing poll if overall timeout not met.")
            if kernel_reported_idle_for_request:
                # If kernel has reported idle for this request, and now the queue is empty, 
                # it's safer to assume all messages for *this request* are done.
                await ctx.info(f"DEBUG: Kernel was idle and IOPub queue is now empty. Ending IOPub loop for msg_id {msg_id}.")
                break
            await asyncio.sleep(0.1) # Brief pause to prevent tight loop if kernel is slow to respond but not yet idle for request.
            continue 
        except Exception as e:
            await ctx.error(f"Error processing IOPub message: {e}")
            outputs.append(f"Exception while processing IOPub message: {e}")
            break
            
    # Shell Reply Message Processing (after IOPub loop)
    shell_reply_status = "unknown"
    try:
        shell_reply = await asyncio.to_thread(kc.get_shell_msg, timeout=10) 
        if shell_reply['parent_header'].get('msg_id') == msg_id:
            content = shell_reply['content']
            shell_reply_status = content['status']
            outputs.insert(0, f"Status: {shell_reply_status}") 

            if shell_reply_status == 'error':
                outputs.append(f"  Shell Error Name: {content.get('ename', 'N/A')}")
                outputs.append(f"  Shell Error Value: {content.get('evalue', 'N/A')}")
                tb = content.get('traceback', [])
                if tb:
                    outputs.append("  Shell Traceback:")
                    outputs.extend([f"    {line}" for line in tb])
            elif shell_reply_status == 'ok':
                outputs.append(f"  Execution Count: {content.get('execution_count', 'N/A')}")
        else:
            outputs.insert(0, f"Status: error_shell_reply_mismatch")
            outputs.append(f"Shell reply (msg_id {shell_reply['parent_header'].get('msg_id')}) was not for the current command (msg_id {msg_id}).")
    except queue.Empty:
        outputs.insert(0, f"Status: error_shell_reply_timeout")
        outputs.append("Timeout waiting for shell reply from IPython kernel.")
    except Exception as e:
        outputs.insert(0, f"Status: error_shell_reply_exception")
        await ctx.error(f"Error getting shell reply: {e}")
        outputs.append(f"Exception while getting shell reply: {e}")
            
    return "\n".join(filter(None, outputs))

@mcp.tool()
async def clear_kernel(ctx: Context) -> str:
    """
    Clears all variables and resets the IPython kernel environment using '%reset -f'.
    """
    await ctx.info("Attempting to clear IPython kernel environment with '%reset -f'...")
    reset_command_output = await send_command("%reset -f", ctx) 
    
    # Check the actual output from send_command for success/failure
    if "Status: ok" in reset_command_output and "error" not in reset_command_output.lower():
        return f"IPython kernel environment cleared successfully.\nDetails:\n{reset_command_output}"
    else:
        return f"IPython kernel clear command finished with potential issues.\nDetails:\n{reset_command_output}"

def main():
    atexit.register(shutdown_ipython_kernel)
    try:
        start_ipython_kernel()
        print("Attempting to run FastMCP server with IPython backend...")
        mcp.run() 
    except Exception as e:
        print(f"Error running FastMCP server or starting kernel: {e}")
    finally:
        print("FastMCP server run loop finished or error occurred.")
        print("Exiting application. Kernel shutdown will be handled by atexit.")

if __name__ == "__main__":
    main()