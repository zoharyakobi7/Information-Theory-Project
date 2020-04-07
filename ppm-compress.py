"""
Compression using PPM code (prediction by partial matching) with arithmetic coding.

To compress dickens text file please run in the terminal:
    python ppm_compress.py InputFile OutputFile
In our case the input file is 'dickens.txt' and the output file is the compressed file, can be called for example
'compressed_dickens.txt'

Note: Please make sure you have python version >=3.
"""

import contextlib
import sys
import arithmeticcoding
import ppmmodel

# Must be at least -1 and match ppm_decompress.py.
MODEL_ORDER = 3


def compress(inp, bitout):
    """
    Set up encoder and model. In this PPM model, symbol 256 represents EOF. Its frequency is 1 in the order -1
    context but its frequency is 0 in all other contexts (which have non-negative order).
    """
    enc = arithmeticcoding.ArithmeticEncoder(32, bitout)
    model = ppmmodel.PpmModel(MODEL_ORDER, 257, 256)
    history = []

    while True:
        # Read and encode one byte
        symbol = inp.read(1)
        if len(symbol) == 0:
            break
        symbol = symbol[0]
        encode_symbol(model, history, symbol, enc)
        model.increment_contexts(history, symbol)

        if model.model_order >= 1:
            # Prepend current symbol, dropping oldest symbol if necessary
            if len(history) == model.model_order:
                history.pop()
            history.insert(0, symbol)

    encode_symbol(model, history, 256, enc)  # EOF
    # Flush remaining code bits
    enc.finish()


def encode_symbol(model, history, symbol, enc):
    """
    Try to use highest order context that exists based on the history suffix, such
    that the next symbol has non-zero frequency. When symbol 256 is produced at a context
    at any non-negative order, it means "escape to the next lower order with non-empty
    context". When symbol 256 is produced at the order -1 context, it means "EOF".
    """
    for order in reversed(range(len(history) + 1)):
        ctx = model.root_context
        for sym in history[: order]:
            assert ctx.subcontexts is not None
            ctx = ctx.subcontexts[sym]
            if ctx is None:
                break
        else:  # ctx is not None
            if symbol != 256 and ctx.frequencies.get(symbol) > 0:
                enc.write(ctx.frequencies, symbol)
                return
            # Else write context escape symbol and continue decrementing the order
            enc.write(ctx.frequencies, 256)
    # Logic for order = -1
    enc.write(model.order_minus1_freqs, symbol)


def final_function(args):
    """
    Final function to compress the given text file with PPM compression.
    """
    # Handle command line arguments
    if len(args) != 2:
        sys.exit("Usage: python ppm_compress.py InputFile OutputFile")
    inputfile = args[0]
    outputfile = args[1]

    # Perform file compression
    with open(inputfile, "rb") as inp, \
            contextlib.closing(arithmeticcoding.BitOutputStream(open(outputfile, "wb"))) as bitout:
        compress(inp, bitout)


if __name__ == "__main__":
    final_function(sys.argv[1:])
