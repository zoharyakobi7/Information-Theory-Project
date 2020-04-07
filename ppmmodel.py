"""
PPM (prediction by partial matching) model using arithmetic coding. Full explanation on PPM compression algorithm
can be found in the pdf file that is in our github page.
"""

import arithmeticcoding


class PpmModel(object):
    """
    Main class to implement out PPM model.
    """

    def __init__(self, order, symbollimit, escapesymbol):
        # order must be at least -1, symbol limit must be at least 0, and the escape symbol must be a positive value
        # and smaller than symbol limit
        if order < -1 or symbollimit <= 0 or not (0 <= escapesymbol < symbollimit):
            raise ValueError()
        self.model_order = order  # order of the model
        self.symbol_limit = symbollimit  # symbol limit
        self.escape_symbol = escapesymbol  # escape symbol

        # building frequency table
        if order >= 0:
            self.root_context = PpmModel.Context(symbollimit, order >= 1)
            self.root_context.frequencies.increment(escapesymbol)
        else:
            self.root_context = None
        self.order_minus1_freqs = arithmeticcoding.FlatFrequencyTable(symbollimit)

    def increment_contexts(self, history, symbol):
        if self.model_order == -1:
            return
        # if the length of the history bytes is bigger than the model's order or if the symbol is bigger than the
        # symbol limit raise an error
        if len(history) > self.model_order or not (0 <= symbol < self.symbol_limit):
            raise ValueError()

        ctx = self.root_context
        # increments the frequency of the given symbol.
        ctx.frequencies.increment(symbol)
        for (i, sym) in enumerate(history):
            subctxs = ctx.subcontexts
            assert subctxs is not None

            if subctxs[sym] is None:
                # rebuild the context
                subctxs[sym] = PpmModel.Context(self.symbol_limit, i + 1 < self.model_order)
                # add the escape symbol to the frequency table
                subctxs[sym].frequencies.increment(self.escape_symbol)
            ctx = subctxs[sym]
            # increment rhe symbol to the frequency table
            ctx.frequencies.increment(symbol)

    class Context(object):
        """
        An internal class to help us implement the PPM model.
        """
        def __init__(self, symbols, hassubctx):
            self.frequencies = arithmeticcoding.SimpleFrequencyTable([0] * symbols)  # frequencies table
            self.subcontexts = ([None] * symbols) if hassubctx else None
