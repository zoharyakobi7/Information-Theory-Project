"""
Huffman compression algorithm. In order to run the code please to the following:

To compress dickens text file please run in the terminal:
    python Huffman.py compress dickens.txt
You will get the file 'dickens_compress.bin'. This is the compressed file. Moreover, you will get a calculation of
how long the compression was taking and how many percents the size of the compressed file is from the original file.

To decompress dickens text file please run in the terminal:
    python Huffman.py decompress dickens_compress.bin
You will get the file 'dickens_decompressed.txt'. This is the file after decompression. Moreover, you will get a
calculation of how long the decompression was taking. You can also check and see the decompressed file is equal to
the original one.
"""

import os
import heapq
import collections
import operator
import ast
import sys
import time


class HeapNode:
    """
    Class to help us with the heap
    """
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return other.freq > self.freq


class HuffmanCoding:
    """
    Main class of Huffman coding
    """
    def __init__(self):
        self.heap = []
        self.codes = {}
        self.reverse_mapping = {}

    def make_frequency_dict(self, text):
        """
        make frequency dictionaries with sorted value from low to high
        """
        counted = dict(collections.Counter(text))
        sort = collections.OrderedDict(
            sorted(
                counted.items(),
                key=operator.itemgetter(1),
                reverse=False))
        return sort

    def make_heap_node(self, freq_dict):
        """
        make a heap queue from node
        """
        for key in freq_dict:
            anode = HeapNode(key, freq_dict[key])
            self.heap.append(anode)

    def merge_nodes(self):
        """
        function to build a tree
        """
        while len(self.heap) > 1:
            node1 = heapq.heappop(self.heap)
            node2 = heapq.heappop(self.heap)
            merge = HeapNode(None, node1.freq + node2.freq)
            merge.left = node1
            merge.right = node2
            heapq.heappush(self.heap, merge)

    # from here we have the actual huffman coding

    def encode_helper(self, root, current_code):
        """
        Helper function for encoding
        """
        if root is None:
            return

        if root.char is not None:
            self.codes[root.char] = current_code
            return

        self.encode_helper(root.left, current_code + "0")
        self.encode_helper(root.right, current_code + "1")

    def encode(self):
        """
        Main Function of encoding
        """
        root = heapq.heappop(self.heap)
        current_code = ""
        self.encode_helper(root, current_code)

    def get_encoded_text(self, text):
        """
        Function to create and get the encoded text
        """
        encoded_text = ""
        for char in text:
            encoded_text += self.codes[char]
        return encoded_text

    def pad_encoded_text(self, encoded_text):
        """
        Padding the encoded text
        """
        # get the extra padding of encoded text
        extra_padding = 8 - len(encoded_text) % 8
        for i in range(extra_padding):
            encoded_text += "0"
        # merge the "info" of extra padding in "string/bit" with encoded text
        # so we know how to truncate it later
        padded_info = "{0:08b}".format(extra_padding)
        new_text = padded_info + encoded_text

        return new_text

    def to_byte_array(self, padded_encoded_text):
        """
        Convert to bytes
        """
        if len(padded_encoded_text) % 8 != 0:
            print('not padded properly')
            exit(0)
        b = bytearray()
        for i in range(
                0, len(padded_encoded_text), 8):  # loop every 8 character
            byte = padded_encoded_text[i:i + 8]
            b.append(int(byte, 2))  # base 2
        return b

    def compress(self, filename):
        """
        final function to compress our text file
        """
        start = time.time()
        file_text = open(filename, 'r')
        lipsum = file_text.read()
        # lipsum = lipsum.rstrip()
        file_text.close()

        freq = self.make_frequency_dict(lipsum)
        self.make_heap_node(freq)
        self.merge_nodes()
        self.encode()
        encoded_text = self.get_encoded_text(lipsum)
        padded_encoded_text = self.pad_encoded_text(encoded_text)
        byte_array_huff = self.to_byte_array(padded_encoded_text)

        # write header
        filename_split = filename.split('.')
        js = open(filename_split[0] + "_compressed.bin", 'wb')
        strcode = str(self.codes)
        js.write(strcode.encode())
        js.close()

        # append new line for separation
        append = open(filename_split[0] + "_compressed.bin", 'a')
        append.write('\n')
        append.close()

        # append the rest of the "byte array"
        f = open(filename_split[0] + "_compressed.bin", 'ab')
        f.write(bytes(byte_array_huff))
        f.close()

        # MISC
        print('Compression Done!')
        get_original_filesize = os.path.getsize(filename)
        get_compressed_filesize = os.path.getsize(
            filename_split[0] + "_compressed.bin")
        percentage = (get_compressed_filesize / get_original_filesize) * 100
        print(round(percentage, 3), "%")
        end = time.time()
        print(round((end - start), 3), "s")

    def remove_padding(self, padded_encoded_text):
        """
        Function to remove the padding
        """
        padded_info = padded_encoded_text[:8]
        extra_padding = int(padded_info, 2)
        padded_encoded_text = padded_encoded_text[8:]
        encoded_text = padded_encoded_text[:-extra_padding]
        return encoded_text

    def decode_text(self, encoded_text):
        """
        Helper function for decoding
        """
        current_code = ""
        decoded_text = ""

        for bit in encoded_text:
            current_code += bit
            if current_code in self.reverse_mapping:
                character = self.reverse_mapping[current_code]
                decoded_text += character
                current_code = ""

        return decoded_text

    def decompress(self, compressedfile):
        """
        Final function for decompression (using the helper function above)
        """
        start = time.time()
        filename_split = compressedfile.split('_')
        # get "header"
        header = open(compressedfile, 'rb').readline().decode()
        # header as object literal
        header = ast.literal_eval(header)
        # reverse mapping for better performance
        self.reverse_mapping = {v: k for k, v in header.items()}

        # get body
        f = open(compressedfile, 'rb')

        # get "body" as list.  [1:] because header
        body = f.readlines()[1:]
        f.close()

        bit_string = ""

        # merge list "body"
        # flattened the byte array
        join_body = [item for sub in body for item in sub]
        for i in join_body:
            bit_string += "{0:08b}".format(i)

        encoded_text = self.remove_padding(bit_string)

        # decompress start here
        current_code = ""
        decoded_text = ""
        for bit in encoded_text:
            current_code += bit
            if current_code in self.reverse_mapping:
                decoded_text += self.reverse_mapping[current_code]
                current_code = ""

        write = open(filename_split[0] + "_decompressed.txt", 'w')
        write.writelines(decoded_text)
        write.close()
        print('Decompression Done!')
        end = time.time()
        print(round((end - start), 3), "s")


huffman = HuffmanCoding()
if __name__ == '__main__':
    if sys.argv[1] == 'compress':
        huffman.compress(sys.argv[2])
    elif sys.argv[1] == 'decompress':
        huffman.decompress(sys.argv[2])
    else:
        print("command not found")
        exit(0)
