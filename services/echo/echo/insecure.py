"""
This is intentionally bad code to test the mandatory Claude Code Review.
This should FAIL the review due to multiple HIGH priority issues.
"""

import os
import subprocess

def execute_user_command(user_input):
    """
    SECURITY VULNERABILITY: Command injection vulnerability!
    Takes user input and executes it directly without sanitization.
    """
    # HIGH PRIORITY: Command injection - executes arbitrary commands
    result = os.system(user_input)
    return result

def execute_shell_command(command):
    """
    SECURITY VULNERABILITY: Shell injection vulnerability!
    """
    # HIGH PRIORITY: Shell injection
    output = subprocess.check_output(command, shell=True)
    return output

def read_file(filename):
    """
    SECURITY VULNERABILITY: Path traversal vulnerability!
    Allows reading arbitrary files on the system.
    """
    # HIGH PRIORITY: Path traversal - no path sanitization
    with open(filename, 'r') as f:
        return f.read()

def sql_query(user_id):
    """
    SECURITY VULNERABILITY: SQL injection vulnerability!
    """
    # HIGH PRIORITY: SQL injection
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query

def store_password(password):
    """
    SECURITY VULNERABILITY: Storing passwords in plain text!
    """
    # HIGH PRIORITY: Plain text password storage
    with open('/tmp/passwords.txt', 'a') as f:
        f.write(password + '\n')
    return True

# CRITICAL BUG: Infinite loop that will hang the application
def broken_loop():
    """This function has a critical bug that causes infinite loop"""
    i = 0
    while i < 10:
        print(f"Count: {i}")
        # BUG: Never increments i, causing infinite loop
        pass

# SEVERE CODE QUALITY: No error handling, poor naming, hardcoded values
def bad_function(x):
    # No type hints, no validation, no error handling
    result = x / 0  # Will always crash
    return result
