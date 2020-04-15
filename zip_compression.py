"""
Zip file compression with a known package of python.

To compress the text file "dickens.txt" please run in the terminal:
    python -m zipfile -c zip_dickens.zip dickens.txt
You will get a file named "zip_dickens.zip" that is the compressed file.

To decompress "zip_dickens.zip" please run in the terminal:
    python zip_compression.py zip_dickens.zip
You will get a folder named "dickens_folder". In it there will be the decompressed file "dickens.txt" that is equal
to the original one.
"""

import sys
import zipfile
with zipfile.ZipFile(sys.argv[1], "r") as zip_ref:
    zip_ref.extractall("dickens_folder")
