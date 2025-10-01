#!/usr/bin/env python3
"""
Test file for demonstrating hooks functionality.
Created to test the PostToolUse file logger hook.

This comment was added by the Edit tool to test the file logger hook.
"""

def calculate_sum(a, b):
    """
    Simple function to demonstrate Python code.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b

def main():
    """Main function for testing."""
    result = calculate_sum(5, 3)
    print(f"5 + 3 = {result}")

    # Test with more numbers
    test_cases = [(10, 20), (100, 200), (-5, 5)]
    for x, y in test_cases:
        print(f"{x} + {y} = {calculate_sum(x, y)}")

if __name__ == "__main__":
    main()