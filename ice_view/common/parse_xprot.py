

import re
import regex as rx
from itertools import chain
import os.path as op


def try_cast(value, key):
    if key.startswith('t'):
        try:
            value = value.strip('"')
        except ValueError:
            pass
    elif key.startswith('b'):
        try:
            value = bool(value)
        except ValueError:
            pass
    elif key.startswith('l') or key.startswith('ul'):
        try:
            value = int(value)
        except ValueError:
            pass
    elif key.startswith('uc'):
        try:
            if value.startswith('0x'):
                value = int(value, 16)
            else:
                value = int(value)
        except ValueError:
            pass
    else:  # try to convert everything else to float
        # obsolete: elif key.startswith('d') or key.startswith('fl'):
        try:
            value = float(value)
        except ValueError:
            pass
    return value


# def parse_array_objs(arrs):
#
#     for arr in arrs:
#         t = rx.findall(r'ParamArray\."(\w+)"', arr.group())
#         if t == []:
#             continue
#         key = t[0]
#
#     r = arrs
#
#     return r


def parse_xprot(buffer):
    xprot = {}
    tokens = re.finditer(r'<Param(?:Bool|Long|String)\."(\w+)">\s*{([^}]*)', buffer)
    tokensDouble = re.finditer(r'<ParamDouble\."(\w+)">\s*{\s*(<Precision>\s*[0-9]*)?\s*([^}]*)', buffer)
    #tokensArray = re.finditer(r"(?s)(?=\<ParamArray\.\".*\"\>\{)(?:(?=.*?\{(?!.*?\1)(.*\}(?!.*\2).*))(?=.*?\}(?!.*?\2)(.*)).)+?.*?(?=\1)[^{]*(?=\2$)", buffer)

    #tokensArray = rx.finditer(r"(?s)(?=\<ParamArray\.\".*\"\>\{)(?:(?=.*?\{(?!.*?\1)(.*\}(?!.*\2).*))(?=.*?\}(?!.*?\2)(.*)).)+?.*?(?=\1)[^{]*(?=\2$)", buffer)
    # r'<ParamArray\."(\w+)">\s+{\s+<Visible>.\"(true|false)\"\s+<MinSize>.(\d+)\s+<MaxSize>.(\d+)\s+<Default>.<(\w+).\"(\w*)\">',
    # r'<ParamArray\."(\w+)">\s+{([^}]*)',
    #t_arr = [item for item in tokensArray]
    #arrs = parse_array_objs(t_arr)

    alltokens = chain(tokens, tokensDouble)

    for t in alltokens:
        name = t.group(1)

        value = re.sub(r'("*)|( *<\w*> *[^\n]*)', '', t.groups()[-1])
        value = re.sub(r'[\t\n\r\f\v]*', '', value.strip())

        if name.startswith('a'):
            out = list()
            for v in value.split():
                out.append(try_cast(v, name[1:]))
            value = out
        else:
            value = try_cast(value, name)

        xprot.update({name: value})

    return xprot


def parse_xprot_wtc(buffer):
    """ from https://github.com/wtclarke/pymapvbvd/blob/master/mapvbvd/read_twix_hdr.py """
    
    xprot = {}

    # captured groups are 1: name, 2: value.
    # param type isn't that useful, since integer values are often stored in string types
    alltokens = re.finditer(
        r'<Param(?:Bool|Long|String|Double)\."(\w+)">\s*{\s*(?:<Precision>\s*[0-9]*)?\s*([^}]*)',
        buffer
    )

    for t in alltokens:
        name = t.group(1)
        value = t.group(2).strip()

        # clean up the obtained values, removing quotes, nested tags and repeated whitespace.
        # Skipped for really lengthy values: most likely nested ASCCONV blocks which aren't handled meaningfully anyway
        if len(value) < 5000:
            value = parse_xprot.re_quotes_and_nested_tags.sub('', value).strip()
            value = parse_xprot.re_repeated_whitespace.sub(' ', value)

            try:
                value = float(value)
            except ValueError:
                pass

        xprot.update({name: value})

    return xprot


parse_xprot.re_repeated_whitespace = re.compile(r'\s+')
parse_xprot.re_quotes_and_nested_tags = re.compile(r'("+)|( *<\w*> *[^\n]*)')


# Test code ----------------------------------------------------------------------

def run_test():

    #fname_test_data = op.join(op.dirname(__file__), '_data_test', 'MiniHead_ima_00001.IceHead')
    #fname_test_data = op.join(op.dirname(__file__), '_data_test', 'MiniHead_spe_00001_short.IceHead')
    fname_test_data = op.join(op.dirname(__file__), '_data_test', 'MiniHead_spe_00001.IceHead')

    with open(fname_test_data) as f:
        data = f.read()
        
    xp = parse_xprot(data)

    bob = 11

# Other useful things https://github.com/jdoepfert/roipoly.py/blob/master/roipoly/roipoly.py
# for drawing Polygons on image with x,y pairs


if __name__ == '__main__':

    run_test()
    
    bob = 11