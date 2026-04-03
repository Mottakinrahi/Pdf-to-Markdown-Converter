"""CLI wrapper — python app.py input.pdf output.md"""
import sys
from converter import convert

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python app.py input.pdf output.md')
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])