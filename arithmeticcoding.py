"""
This is an implementation of arithmetic coding to help us implement PPM model. Full explanation is attached in
a separated pdf file (you can find it in our github page).
"""

import sys

# make sure your python version is more than 3
python3 = sys.version_info.major >= 3


# ---- Arithmetic coding core classes ----

class ArithmeticCoderBase(object):
    """
    This is the basic class that provides the behaviours and characteristics that  arithmetic coding encoders and
    decoders share.
    """

    # Constructs an arithmetic coder, which initializes the code range.
    def __init__(self, numbits):
        # Number of bits for the 'low' and 'high' state variables. Must be at least 1.
        if numbits < 1:
            raise ValueError("State size out of range")
        self.num_state_bits = numbits
        # Maximum range (high+1-low) during coding
        self.full_range = 1 << self.num_state_bits
        # The top bit at width num_state_bits, which is 0100...000.
        self.half_range = self.full_range >> 1  # Non-zero
        # The second highest bit at width num_state_bits, which is 0010...000. This is zero when num_state_bits=1.
        self.quarter_range = self.half_range >> 1  # Can be zero
        # Minimum range (high+1-low) during coding (non-trivial), which is 0010...010.
        self.minimum_range = self.quarter_range + 2  # At least 2
        self.maximum_total = self.minimum_range
        # Bit mask of num_state_bits ones, which is 0111...111.
        self.state_mask = self.full_range - 1
        # Low end of this arithmetic coder's current range.
        self.low = 0
        # High end of this arithmetic coder's current range
        self.high = self.state_mask

    def update(self, freqs, symbol):
        """
        Updates the code range (low and high) of this arithmetic coder as a result of processing the given symbol
        with the given frequency table.
        """
        # State check
        low = self.low
        high = self.high
        if low >= high or (low & self.state_mask) != low or (high & self.state_mask) != high:
            raise AssertionError("Low or high out of range")
        range = high - low + 1
        if not (self.minimum_range <= range <= self.full_range):
            raise AssertionError("Range out of range")

        # Frequency table values check
        total = freqs.get_total()
        symlow = freqs.get_low(symbol)
        symhigh = freqs.get_high(symbol)
        if symlow == symhigh:
            raise ValueError("Symbol has zero frequency")
        if total > self.maximum_total:
            raise ValueError("Cannot code symbol because total is too large")

        # Update range
        newlow = low + symlow * range // total
        newhigh = low + symhigh * range // total - 1
        self.low = newlow
        self.high = newhigh

        # While low and high have the same top bit value, shift them out
        while ((self.low ^ self.high) & self.half_range) == 0:
            self.shift()
            self.low = ((self.low << 1) & self.state_mask)
            self.high = ((self.high << 1) & self.state_mask) | 1
        # Now low's top bit must be 0 and high's top bit must be 1

        # While low's top two bits are 01 and high's are 10, delete the second highest bit of both
        while (self.low & ~self.high & self.quarter_range) != 0:
            self.underflow()
            self.low = (self.low << 1) ^ self.half_range
            self.high = ((self.high ^ self.half_range) << 1) | self.half_range | 1

    # when the top bit of 'low' and 'high' are equal.
    def shift(self):
        raise NotImplementedError()

    # when low=01(...) and high=10(...).
    def underflow(self):
        raise NotImplementedError()


class ArithmeticEncoder(ArithmeticCoderBase):
    """
    Encodes symbols and writes to an arithmetic-coded bit stream. Inherits from the basic class (above).
    """

    # Constructs an arithmetic coding encoder based on the given bit output stream.
    def __init__(self, numbits, bitout):
        super(ArithmeticEncoder, self).__init__(numbits)
        # The underlying bit output stream.
        self.output = bitout
        # Number of saved underflow bits
        self.num_underflow = 0

    def write(self, freqs, symbol):
        """
        Encodes the given symbol based on the given frequency table. This updates this arithmetic coder's state
        and may write out some bits.
        """
        if not isinstance(freqs, CheckedFrequencyTable):
            freqs = CheckedFrequencyTable(freqs)
        self.update(freqs, symbol)

    def finish(self):
        self.output.write(1)

    def shift(self):
        bit = self.low >> (self.num_state_bits - 1)
        self.output.write(bit)

        # Write out the saved underflow bits
        for _ in range(self.num_underflow):
            self.output.write(bit ^ 1)
        self.num_underflow = 0

    def underflow(self):
        self.num_underflow += 1


class ArithmeticDecoder(ArithmeticCoderBase):
    """
    Reads from an arithmetic-coded bit stream and decodes symbols. Inherits from the base class (above).
    """

    # Constructs an arithmetic coding decoder based on the given bit input stream, and fills the code bits.
    def __init__(self, numbits, bitin):
        super(ArithmeticDecoder, self).__init__(numbits)
        # The underlying bit input stream.
        self.input = bitin
        # The current raw code bits being buffered, which is always in the range [low, high].
        self.code = 0
        for _ in range(self.num_state_bits):
            self.code = self.code << 1 | self.read_code_bit()

    def read(self, freqs):
        """
        Decodes the next symbol based on the given frequency table and returns it. Also updates this arithmetic
        coder's state and may read in some bits.
        """
        if not isinstance(freqs, CheckedFrequencyTable):
            freqs = CheckedFrequencyTable(freqs)

        # Translate from coding range scale to frequency table scale
        total = freqs.get_total()
        if total > self.maximum_total:
            raise ValueError("Cannot decode symbol because total is too large")
        range = self.high - self.low + 1
        offset = self.code - self.low
        value = ((offset + 1) * total - 1) // range
        assert value * range // total <= offset
        assert 0 <= value < total

        # A kind of binary search. Find highest symbol such that freqs.get_low(symbol) <= value.
        start = 0
        end = freqs.get_symbol_limit()
        while end - start > 1:
            middle = (start + end) >> 1
            if freqs.get_low(middle) > value:
                end = middle
            else:
                start = middle
        assert start + 1 == end

        symbol = start
        assert freqs.get_low(symbol) * range // total <= offset < freqs.get_high(symbol) * range // total
        self.update(freqs, symbol)
        if not (self.low <= self.code <= self.high):
            raise AssertionError("Code out of range")
        return symbol

    def shift(self):
        self.code = ((self.code << 1) & self.state_mask) | self.read_code_bit()

    def underflow(self):
        self.code = (self.code & self.half_range) | ((self.code << 1) & (self.state_mask >> 1)) | self.read_code_bit()

    def read_code_bit(self):
        """
        Returns the next bit (0 or 1) from the input stream. The end of stream is treated as an infinite number of
        trailing zeros.
        """
        temp = self.input.read()
        if temp == -1:
            temp = 0
        return temp


# ---- Frequency table classes ----

class FrequencyTable(object):
    """
    A table of symbol frequencies. The table holds data for symbols numbered from 0 to get_symbol_limit()-1.
    Each symbol has a frequency, which is a non-negative integer. Frequency table objects are primarily used for
    getting cumulative symbol frequencies.
    """
    # Returns the number of symbols in this frequency table, which is a positive number.
    def get_symbol_limit(self):
        raise NotImplementedError()

    # Returns the frequency of the given symbol. The returned value is at least 0.
    def get(self, symbol):
        raise NotImplementedError()

    # Sets the frequency of the given symbol to the given value (frequency must be at least 0).
    def set(self, symbol, freq):
        raise NotImplementedError()

    # Increments the frequency of the given symbol.
    def increment(self, symbol):
        raise NotImplementedError()

    # Returns the total of all symbol frequencies. (at least 0).
    def get_total(self):
        raise NotImplementedError()

    # Returns the sum of the frequencies of all the symbols strictly below the given symbol value. (at least 0).
    def get_low(self, symbol):
        raise NotImplementedError()

    # Returns the sum of the frequencies of the given symbol and all the symbols below. (at least 0).
    def get_high(self, symbol):
        raise NotImplementedError()


class FlatFrequencyTable(FrequencyTable):
    """
    An immutable frequency table where every symbol has the same frequency of 1.
    """

    # Constructs a flat frequency table with the given number of symbols.
    def __init__(self, numsyms):
        if numsyms < 1:
            raise ValueError("Number of symbols must be positive")
        self.numsymbols = numsyms  # Total number of symbols, which is at least 1

    # Returns the number of symbols in this table, which is at least 1.
    def get_symbol_limit(self):
        return self.numsymbols

    # Returns the frequency of the given symbol, which is always 1.
    def get(self, symbol):
        self._check_symbol(symbol)
        return 1

    # Returns the total of all symbol frequencies
    def get_total(self):
        return self.numsymbols

    # Returns the sum of the frequencies of all the symbols strictly below the given symbol value.
    def get_low(self, symbol):
        self._check_symbol(symbol)
        return symbol

    def get_high(self, symbol):
        """
        Returns the sum of the frequencies of the given symbol and all the symbols below. The returned value is
        equal to 'symbol' + 1.
        """
        self._check_symbol(symbol)
        return symbol + 1

    # Returns silently if 0 <= symbol < numsymbols, otherwise raises an exception.
    def _check_symbol(self, symbol):
        if 0 <= symbol < self.numsymbols:
            return
        else:
            raise ValueError("Symbol out of range")

    # Returns a string representation of this frequency table. The format is subject to change.
    def __str__(self):
        return "FlatFrequencyTable={}".format(self.numsymbols)

    def set(self, symbol, freq):
        raise NotImplementedError()

    def increment(self, symbol):
        raise NotImplementedError()


class SimpleFrequencyTable(FrequencyTable):
    """
    A mutable table of symbol frequencies. The number of symbols cannot be changed after construction.
    """

    def __init__(self, freqs):
        if isinstance(freqs, FrequencyTable):
            numsym = freqs.get_symbol_limit()
            self.frequencies = [freqs.get(i) for i in range(numsym)]
        else:  # Assume it is a sequence type
            self.frequencies = list(freqs)  # Make copy

        # 'frequencies' is a list of the frequency for each symbol. Its length is at least 1, and each element
        # is non-negative.
        if len(self.frequencies) < 1:
            raise ValueError("At least 1 symbol needed")
        for freq in self.frequencies:
            if freq < 0:
                raise ValueError("Negative frequency")

        # Always equal to the sum of 'frequencies'
        self.total = sum(self.frequencies)

        # cumulative[i] is the sum of 'frequencies' from 0 (inclusive) to i (exclusive).
        # Initialized lazily. When it is not None, the data is valid.
        self.cumulative = None

    # Returns the number of symbols in this frequency table, which is at least 1.
    def get_symbol_limit(self):
        return len(self.frequencies)

    # Returns the frequency of the given symbol. The returned value is at least 0.
    def get(self, symbol):
        self._check_symbol(symbol)
        return self.frequencies[symbol]

    def set(self, symbol, freq):
        """
        Sets the frequency of the given symbol to the given value. The frequency value
        must be at least 0. If an exception is raised, then the state is left unchanged.
        """
        self._check_symbol(symbol)
        if freq < 0:
            raise ValueError("Negative frequency")
        temp = self.total - self.frequencies[symbol]
        assert temp >= 0
        self.total = temp + freq
        self.frequencies[symbol] = freq
        self.cumulative = None

    def increment(self, symbol):
        """
        Increments the frequency of the given symbol.
        """
        self._check_symbol(symbol)
        self.total += 1
        self.frequencies[symbol] += 1
        self.cumulative = None

    def get_total(self):
        """
        Returns the total of all symbol frequencies. The returned value is at least 0 and is always equal to
        get_high(get_symbol_limit() - 1).
        """
        return self.total

    def get_low(self, symbol):
        """
        Returns the sum of the frequencies of all the symbols strictly below the given symbol value. The returned
        value is at least 0.
        """
        self._check_symbol(symbol)
        if self.cumulative is None:
            self._init_cumulative()
        return self.cumulative[symbol]

    def get_high(self, symbol):
        """
        Returns the sum of the frequencies of the given symbol and all the symbols below. The returned value is at
        least 0.
        """
        self._check_symbol(symbol)
        if self.cumulative is None:
            self._init_cumulative()
        return self.cumulative[symbol + 1]

    def _init_cumulative(self):
        """
        Recomputes the array of cumulative symbol frequencies.
        """
        cumul = [0]
        sum = 0
        for freq in self.frequencies:
            sum += freq
            cumul.append(sum)
        assert sum == self.total
        self.cumulative = cumul

    # Returns silently if 0 <= symbol < len(frequencies), otherwise raises an exception.
    def _check_symbol(self, symbol):
        if 0 <= symbol < len(self.frequencies):
            return
        else:
            raise ValueError("Symbol out of range")

    def __str__(self):
        """
        Returns a string representation of this frequency table, useful for debugging only, and the format is subject
        to change.
        """
        result = ""
        for (i, freq) in enumerate(self.frequencies):
            result += "{}\t{}\n".format(i, freq)
        return result


class CheckedFrequencyTable(FrequencyTable):
    """
    A wrapper that checks the preconditions (arguments) and post-conditions (return value) of all
    the frequency table methods. Useful for finding faults in a frequency table implementation.
    """
    def __init__(self, freqtab):
        # The underlying frequency table that holds the data
        self.freqtable = freqtab

    def get_symbol_limit(self):
        result = self.freqtable.get_symbol_limit()
        if result <= 0:
            raise AssertionError("Non-positive symbol limit")
        return result

    def get(self, symbol):
        result = self.freqtable.get(symbol)
        if not self._is_symbol_in_range(symbol):
            raise AssertionError("ValueError expected")
        if result < 0:
            raise AssertionError("Negative symbol frequency")
        return result

    def get_total(self):
        result = self.freqtable.get_total()
        if result < 0:
            raise AssertionError("Negative total frequency")
        return result

    def get_low(self, symbol):
        if self._is_symbol_in_range(symbol):
            low = self.freqtable.get_low(symbol)
            high = self.freqtable.get_high(symbol)
            if not (0 <= low <= high <= self.freqtable.get_total()):
                raise AssertionError("Symbol low cumulative frequency out of range")
            return low
        else:
            self.freqtable.get_low(symbol)
            raise AssertionError("ValueError expected")

    def get_high(self, symbol):
        if self._is_symbol_in_range(symbol):
            low = self.freqtable.get_low(symbol)
            high = self.freqtable.get_high(symbol)
            if not (0 <= low <= high <= self.freqtable.get_total()):
                raise AssertionError("Symbol high cumulative frequency out of range")
            return high
        else:
            self.freqtable.get_high(symbol)
            raise AssertionError("ValueError expected")

    def __str__(self):
        return "CheckedFrequencyTable (" + str(self.freqtable) + ")"

    def set(self, symbol, freq):
        self.freqtable.set(symbol, freq)
        if not self._is_symbol_in_range(symbol) or freq < 0:
            raise AssertionError("ValueError expected")

    def increment(self, symbol):
        self.freqtable.increment(symbol)
        if not self._is_symbol_in_range(symbol):
            raise AssertionError("ValueError expected")

    def _is_symbol_in_range(self, symbol):
        return 0 <= symbol < self.get_symbol_limit()


# ---- Bit-oriented I/O streams ----

class BitInputStream(object):
    """
    A stream of bits that can be read. Because they come from an underlying byte stream, the total number of bits is
    always a multiple of 8. The bits are read in big endian.
    """

    # Constructs a bit input stream based on the given byte input stream.
    def __init__(self, inp):
        # The underlying byte stream to read from
        self.input = inp
        # Either in the range [0x00, 0xFF] if bits are available, or -1 if end of stream is reached
        self.currentbyte = 0
        # Number of remaining bits in the current byte, always between 0 and 7 (inclusive)
        self.numbitsremaining = 0

    def read(self):
        """
        Reads a bit from this stream. Returns 0 or 1 if a bit is available, or -1 if the end of stream is reached.
        The end of stream always occurs on a byte boundary.
        """
        if self.currentbyte == -1:
            return -1
        if self.numbitsremaining == 0:
            temp = self.input.read(1)
            if len(temp) == 0:
                self.currentbyte = -1
                return -1
            self.currentbyte = temp[0] if python3 else ord(temp)
            self.numbitsremaining = 8
        assert self.numbitsremaining > 0
        self.numbitsremaining -= 1
        return (self.currentbyte >> self.numbitsremaining) & 1

    def read_no_eof(self):
        """
        Reads a bit from this stream. Returns 0 or 1 if a bit is available, or raises an EOFError if the end of stream
        is reached. The end of stream always occurs on a byte boundary.
        """
        result = self.read()
        if result != -1:
            return result
        else:
            raise EOFError()

    def close(self):
        """
        Closes this stream and the underlying input stream.
        """
        self.input.close()
        self.currentbyte = -1
        self.numbitsremaining = 0


class BitOutputStream(object):
    """
    A stream where bits can be written to. Because they are written to an underlying byte stream, the end of the
    stream is padded with 0's up to a multiple of 8 bits. The bits are written in big endian.
    """

    # Constructs a bit output stream based on the given byte output stream.
    def __init__(self, out):
        self.output = out  # The underlying byte stream to write to
        self.currentbyte = 0  # The accumulated bits for the current byte, always in the range [0x00, 0xFF]
        self.numbitsfilled = 0  # Number of accumulated bits in the current byte, always between 0 and 7 (inclusive)

    def write(self, b):
        """
        Writes a bit to the stream. The given bit must be 0 or 1.
        """
        if b not in (0, 1):
            raise ValueError("Argument must be 0 or 1")
        self.currentbyte = (self.currentbyte << 1) | b
        self.numbitsfilled += 1
        if self.numbitsfilled == 8:
            towrite = bytes((self.currentbyte,)) if python3 else chr(self.currentbyte)
            self.output.write(towrite)
            self.currentbyte = 0
            self.numbitsfilled = 0

    def close(self):
        """
        Closes this stream and the underlying output stream. If called when this bit stream is not at a byte boundary,
        then the minimum number of "0" bits (between 0 and 7 of them) are written as padding to reach the next byte
        boundary.
        """
        while self.numbitsfilled != 0:
            self.write(0)
        self.output.close()
