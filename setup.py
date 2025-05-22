from setuptools import setup, find_packages

setup(
    name='mcp-ipython',
    version='0.0.1',
    description='A FastMCP backend that interfaces with an IPython kernel to execute Python commands and manage the kernel environment.',
    long_description=open('README.md').read() if 'README.md' else '',
    long_description_content_type='text/markdown',
    author='Kreijstal',
    license='AGPL-3.0-or-later',
    packages=find_packages(),
    py_modules=['server'], # Since server.py is the main module
    install_requires=[
        'fastmcp',
        'jupyter_client',
        # Add any other dependencies found in server.py, e.g., asyncio, atexit, queue, time
        # These are standard library modules, so no need to list them here.
    ],
    classifiers=[
        'Programming Language :: Python :: 3',

        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Shells',
    ],
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'mcp-ipython-server=server:main',
        ],
    },
)