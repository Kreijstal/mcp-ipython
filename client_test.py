import asyncio
import traceback
from fastmcp import Client

async def main():
    # The server.py script uses mcp.run() which defaults to STDIO.
    # The FastMCP client can connect to a script using its path and manage the server process.
    server_script_path = "server.py" # Assumes server.py is in the same directory

    print(f"Attempting to connect to FastMCP server script: {server_script_path}")
    print("The client will start the server.py script as a subprocess.")
    print("You should see output from server.py (kernel starting) before client tests begin.")

    try:
        # The Client will start 'python server.py' (or equivalent) as a subprocess.
        # If 'python' isn't in PATH or server.py needs a specific python interpreter,
        # you might need to adjust how the server is run or how the client connects.
        # For now, we assume 'python server.py' works from the command line.
        async with Client(server_script_path) as client: # Corrected client initialization for local script
            print("\nSuccessfully connected to the FastMCP server (server.py subprocess).")

            # 1. List tools
            print("\n--- Test 1: Listing available tools ---")
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]
            print(f"Available tools: {tool_names}")
            assert "send_command" in tool_names, "send_command tool not found!"
            assert "clear_kernel" in tool_names, "clear_kernel tool not found!"
            print("send_command and clear_kernel tools found. Test 1 PASSED.")

            # 2. Send a command to define a variable and print it
            print("\n--- Test 2: 'send_command' (define and print 'x') ---")
            command1 = "x = 42\nprint(f'The value of x is {x}')"
            print(f"Sending command: {command1}")
            result1 = await client.call_tool("send_command", {"command": command1})
            print(f"DEBUG: Type of result1: {type(result1)}")
            print(f"DEBUG: Value of result1: {result1}")
            # Handle result1 possibly being a list of Content objects
            actual_text_output1 = ""
            if isinstance(result1, list) and len(result1) > 0 and hasattr(result1[0], 'text'):
                actual_text_output1 = result1[0].text
            elif hasattr(result1, 'text'): # If it's a regular ToolResult (or similar)
                actual_text_output1 = result1.text
            else:
                print(f"WARNING: result1 is not a list of Content objects or a ToolResult with .text. Type: {type(result1)}, Value: {result1}")

            print(f"Result of defining and printing 'x':\n{actual_text_output1}")
            assert "The value of x is 42" in actual_text_output1, f"Output did not contain 'The value of x is 42'. Got: '{actual_text_output1}'"
            assert "Status: ok" in actual_text_output1, f"Status was not 'ok'. Got: '{actual_text_output1}'"
            print("Test 2 PASSED.")

            # 3. Send another command to check the variable 'x'
            print("\n--- Test 3: 'send_command' (check 'x' again) ---")
            command2 = "print(f'x is still {x}')"
            print(f"Sending command: {command2}")
            result2 = await client.call_tool("send_command", {"command": command2})
            actual_text_output2 = ""
            if isinstance(result2, list) and len(result2) > 0 and hasattr(result2[0], 'text'):
                actual_text_output2 = result2[0].text
            elif hasattr(result2, 'text'):
                actual_text_output2 = result2.text
            else:
                print(f"WARNING: result2 is not as expected. Type: {type(result2)}, Value: {result2}")

            print(f"Result of checking 'x' again:\n{actual_text_output2}")
            assert "x is still 42" in actual_text_output2, f"Output did not contain 'x is still 42'. Got: '{actual_text_output2}'"
            assert "Status: ok" in actual_text_output2, f"Status was not 'ok'. Got: '{actual_text_output2}'"
            print("Test 3 PASSED.")

            # 4. Clear the kernel
            print("\n--- Test 4: 'clear_kernel' ---")
            print("Calling clear_kernel tool...")
            clear_result = await client.call_tool("clear_kernel", {})
            actual_text_clear_result = ""
            if isinstance(clear_result, list) and len(clear_result) > 0 and hasattr(clear_result[0], 'text'):
                actual_text_clear_result = clear_result[0].text
            elif hasattr(clear_result, 'text'):
                actual_text_clear_result = clear_result.text
            else:
                print(f"WARNING: clear_result is not as expected. Type: {type(clear_result)}, Value: {clear_result}")

            print(f"Result of clearing kernel:\n{actual_text_clear_result}")
            assert "IPython kernel environment cleared" in actual_text_clear_result or \
                   "Kernel reset command executed successfully" in actual_text_clear_result or \
                   "status: ok" in actual_text_clear_result.lower(), f"Kernel clear confirmation not found. Got: '{actual_text_clear_result}'"
            print("Test 4 PASSED.")


            # 5. Try to access the variable 'x' again (should fail or be undefined)
            print("\n--- Test 5: 'send_command' after clear (check 'x' - should be undefined) ---")
            command3 = "print(x)" # This should now cause a NameError
            print(f"Sending command: {command3}")
            result3 = await client.call_tool("send_command", {"command": command3})
            actual_text_output3 = ""
            if isinstance(result3, list) and len(result3) > 0 and hasattr(result3[0], 'text'):
                actual_text_output3 = result3[0].text
            elif hasattr(result3, 'text'):
                actual_text_output3 = result3.text
            else:
                print(f"WARNING: result3 is not as expected. Type: {type(result3)}, Value: {result3}")

            print(f"Result of trying to print 'x' after clear:\n{actual_text_output3}")
            assert "Status: error" in actual_text_output3, f"Status was not 'error' for undefined variable. Got: '{actual_text_output3}'"
            assert "NameError" in actual_text_output3 or \
                   "name 'x' is not defined" in actual_text_output3.lower(), f"NameError for 'x' not found after clear. Got: '{actual_text_output3}'"
            print("Test 5 PASSED: 'x' is undefined after kernel clear, as expected.")

            # 6. Test a multi-line command with an expression result
            print("\n--- Test 6: 'send_command' with multi-line and expression result ---")
            command4 = "y = 10\nz = y * 2\nz" # Last line is an expression
            print(f"Sending command: {command4}")
            result4 = await client.call_tool("send_command", {"command": command4})
            actual_text_output4 = ""
            if isinstance(result4, list) and len(result4) > 0 and hasattr(result4[0], 'text'):
                actual_text_output4 = result4[0].text
            elif hasattr(result4, 'text'):
                actual_text_output4 = result4.text
            else:
                print(f"WARNING: result4 is not as expected. Type: {type(result4)}, Value: {result4}")

            print(f"Result of multi-line command with expression:\n{actual_text_output4}")
            assert "Status: ok" in actual_text_output4, f"Status was not 'ok' for expression command. Got: '{actual_text_output4}'"
            # IPython's execute_result for an expression 'z' would show '20'
            assert "Result: 20" in actual_text_output4 or "Out[1]: 20" in actual_text_output4 or "20" in actual_text_output4.splitlines()[-1] if actual_text_output4 else False, f"Expression result '20' not found. Got: '{actual_text_output4}'"
            print("Test 6 PASSED.")

            print("\n---------------------------------")
            # 7. Test multi-line function definition and execution
            print("\n--- Test 7: 'send_command' with multi-line function ---")
            command5 = "def greet(name):\n    return f'Hello, {name}!'\n\ngreet('FastMCP')"
            print(f"Sending command: {command5}")
            result5 = await client.call_tool("send_command", {"command": command5})
            actual_text_output5 = ""
            if isinstance(result5, list) and len(result5) > 0 and hasattr(result5[0], 'text'):
                actual_text_output5 = result5[0].text
            elif hasattr(result5, 'text'):
                actual_text_output5 = result5.text
            else:
                print(f"WARNING: result5 is not as expected. Type: {type(result5)}, Value: {result5}")

            print(f"Result of multi-line function test:\n{actual_text_output5}")
            assert "Status: ok" in actual_text_output5, f"Status was not 'ok' for function test. Got: '{actual_text_output5}'"
            assert "Hello, FastMCP!" in actual_text_output5, f"Function output not found. Got: '{actual_text_output5}'"
            print("Test 7 PASSED: Multi-line function works correctly.")

            print("🎉 All client tests passed! 🎉")
            print("---------------------------------")

    except ConnectionRefusedError:
        print("\n❌ ERROR: Connection refused.")
        print("Make sure server.py is not already running elsewhere if it binds to a specific port (though default STDIO shouldn't have this issue).")
        print("Ensure 'python' is in your PATH and can execute server.py.")
    except Exception as e:
        print(f"\n❌ ERROR: An error occurred during the test: {e}")
        print("Detailed traceback:")
        traceback.print_exc()
        print("\nOne or more tests FAILED.")

if __name__ == "__main__":
    # Ensure that if server.py prints a lot at startup, 
    # we give it a moment. Client usually handles this fine.
    asyncio.run(main())
