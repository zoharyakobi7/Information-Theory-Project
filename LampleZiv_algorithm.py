'''lample ziv algorithm from scratch'''


'''read dickens file'''
reuven_file = []
with open('dickens.txt', 'r',encoding='latin1') as fh:
    for line in fh:
        reuven_file.extend(line)
reuven_file = ''.join(reuven_file)


def compress(uncompressed):
    """ compress a string to a list of output symbols """
    # build the dictionary
    dict_size = 256
    dictionary = {}
    for i in range(dict_size):
        dictionary[chr(i)] = i

    result = []

    w = ""
    for c in uncompressed:
        wc = w + c
        if wc in dictionary:
            w = wc
        else:
            result.append(dictionary[w])
            # add wc to the dictionary
            dictionary[wc] = dict_size
            dict_size += 1
            w = c

    # output the code for w
    if w:
        result.append(dictionary[w])

    return result


def decompress(compressed):
    """ decompress a list of output symbols to a string """

    # build the dictionary
    dict_size = 256
    dictionary = {}
    for i in range(dict_size):
        dictionary[i] = chr(i)

    if compressed:
        w = chr(compressed.pop(0))
    else:
        raise (ValueError, "empty")

    result = [w]

    for k in compressed:
        if k in dictionary:
            entry = dictionary[k]
        elif k == len(dictionary):
            entry = w + w[0]
        else:
            raise (ValueError, "Bad compressed k: %d" % k)

        result.append(entry)

        # add (w + entry.[0]) to the dictionary
        dictionary[dict_size] = w + entry[0]
        dict_size += 1

        w = entry

    return result


'''
make the compressed and decompressed files made by lample ziv algorithm
'''
res = compress(reuven_file)
print(res[len(res)-1])
with open('compress_lzw.txt', 'w') as f:
    for item in res:
        f.write("%s," % item)
f.close()

final = decompress(res)
with open('decompress_lzw.txt', 'w') as f:
    for i in range(len(final)):
        try:
            f.write("%s" % final[i])
            pass
        except:
            pass
f.close()
