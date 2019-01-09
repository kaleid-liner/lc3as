import re
import struct
import argparse
import ast


word_pattern = r"""\'.*?\'|".*?"|[^,\s]+"""
label_pattern = r'^[_a-zA-Z][_a-zA-Z0-9]*$'
br_pattern = r'^(?:BR|br)[NZPnzp]{1,3}$'
imm_pattern = r'^[xX](-?[0-9a-fA-F]+)|#?(-?[0-9]+)$'
reg_pattern = r'^[Rr][0-7]$'
expr_pattern = r'^([_a-zA-Z][_a-zA-Z0-9]*)([+-])([xX](-?[0-9a-fA-F]+)|#?(-?[0-9]+))$'

op_asm = {}
pseudo_asm = {}
keywords = []

symbol_table = {}
orig_address = 0
pc = 0


def reg_op_asm(name):
    def decorate(asm_func):
        op_asm[name] = asm_func
        keywords.append(name)
        return asm_func
    return decorate


def reg_pseudo(name):
    def decorate(asm_func):
        pseudo_asm[name] = asm_func
        keywords.append(name)
        return asm_func
    return decorate


def assemble(words):
    """
    assemble an instruction to its corresponding machine code
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: list of two bytes packed as short representing the machine code of the instruction
    """
    if words[0].startswith('BR'):
        if not re.match(br_pattern, words[0]):
            raise ValueError('expect BR[n|z|p] but get %s' % words[0])
        instrs = [op_asm['BR'](words)]
    elif words[0] in op_asm:
        instrs = [op_asm[words[0]](words)]
    else:
        try:
            instrs = pseudo_asm[words[0]](words)
        except KeyError:
            raise ValueError('%s not a valid opcodes or pseudo op' % words[0])
    return [struct.pack('!H', int(instr, 2)) for instr in instrs]


@reg_op_asm('ADD')
def add_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '0001'
    dr = get_register(words[1])
    sr = get_register(words[2])
    if re.match(imm_pattern, words[3]):
        imm = calc_imm(words[3])
        instr += dr + sr + '1' + int2binary(imm, 5)
    else:
        sr2 = get_register(words[3])
        instr += dr + sr + '000' + sr2
    return instr


@reg_op_asm('AND')
def and_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '0101'
    dr = get_register(words[1])
    sr = get_register(words[2])
    if re.match(imm_pattern, words[3]):
        imm = calc_imm(words[3])
        instr += dr + sr + '1' + int2binary(imm, 5)
    else:
        sr2 = get_register(words[3])
        instr += dr + sr + '000' + sr2
    return instr


@reg_op_asm('BR')
def br_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '0000'
    n, z, p = (str(int(x in words[0])) for x in 'nzp')
    offset = int2binary(calc_offset(words[1]), 9)
    instr += n + z + p + offset
    return instr


@reg_op_asm('JMP')
def jmp_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '1100'
    baser = get_register(words[1])
    instr += '000' + baser + '000000'
    return instr


@reg_op_asm('JSR')
def jsr_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '0100'
    offset = int2binary(calc_offset(words[1]), 11)
    instr += '1' + offset
    return instr


@reg_op_asm('JSRR')
def jsrr_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '0100'
    baser = get_register(words[1])
    instr += '000' + baser + '000000'
    return instr


@reg_op_asm('LD')
def ld_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '0010'
    dr = get_register(words[1])
    offset = int2binary(calc_offset(words[2]), 9)
    instr += dr + offset
    return instr


@reg_op_asm('LDI')
def ldi_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '1010'
    dr = get_register(words[1])
    offset = int2binary(calc_offset(words[2]), 9)
    instr += dr + offset
    return instr


@reg_op_asm('LDR')
def ldr_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '0110'
    dr = get_register(words[1])
    baser = get_register(words[2])
    imm = int2binary(calc_imm(words[3]), 6)
    instr += dr + baser + imm
    return instr


@reg_op_asm('LEA')
def lea_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '1110'
    dr = get_register(words[1])
    offset = int2binary(calc_offset(words[2]), 9)
    instr += dr + offset
    return instr


@reg_op_asm('NOT')
def not_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '1001'
    dr = get_register(words[1])
    sr = get_register(words[2])
    instr += dr + sr + '111111'
    return instr


@reg_op_asm('RET')
def ret_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '1100000111000000'
    return instr


@reg_op_asm('RTI')
def rti_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '1000000000000000'
    return instr


@reg_op_asm('ST')
def st_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '0011'
    sr = get_register(words[1])
    offset = int2binary(calc_offset(words[2]), 9)
    instr += sr + offset
    return instr


@reg_op_asm('STI')
def sti_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '1011'
    sr = get_register(words[1])
    offset = int2binary(calc_offset(words[2]), 9)
    instr += sr + offset
    return instr


@reg_op_asm('STR')
def str_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '0111'
    sr = get_register(words[1])
    baser = get_register(words[2])
    offset = int2binary(calc_offset(words[3]), 6)
    instr += sr + baser + offset
    return instr


@reg_op_asm('TRAP')
def trap_asm(words):
    """
    :param words: list of words in an instruction. ADD R3, R3, #0, eg. is ['ADD', 'R3', 'R3', '#0']
    :return: instruction represented as '01'
    """
    instr = '1111'
    trap_vect = int2binary(calc_imm(words[1]), 8, False)
    return instr + '0000' + trap_vect


@reg_op_asm('GETC')
def getc_asm(words):
    return '1111000000100000'


@reg_op_asm('HALT')
def halt_asm(words):
    return '1111000000100101'


@reg_op_asm('OUT')
def out_asm(words):
    return '1111000000100001'


@reg_op_asm('IN')
def in_asm(words):
    return '1111000000100011'


@reg_op_asm('PUTS')
def puts_asm(words):
    return '1111000000100010'


@reg_pseudo('.ORIG')
def orig_asm(words):
    global orig_address
    orig_address = calc_imm(words[1])
    instr = int2binary(orig_address, 16, False)
    return [instr]


@reg_pseudo('.FILL')
def fill_asm(words):
    instr = int2binary(calc_address(words[1]), 16, False)
    return [instr]


@reg_pseudo('.BLKW')
def blkw_asm(words):
    blk = calc_imm(words[1])
    return ['0' * 16] * blk


@reg_pseudo('.END')
def end_asm(words):
    return []


@reg_pseudo('.STRINGZ')
def stringz_asm(words):
    instrs = []
    for ch in words[1]:
        instrs.append(int2binary(ord(ch), 16, False))
    instrs.append('0000000000000000')
    return instrs


def is_keyword(word):
    return word.upper() in keywords\
            or re.match(br_pattern, word)


def is_label(word):
    try:
        if is_keyword(word)\
                or not re.match(label_pattern, word)\
                or re.match(imm_pattern, word)\
                or re.match(reg_pattern, word):
            return False
        else:
            return True
    except AttributeError:
        return False


def get_register(word):
    if re.match(reg_pattern, word):
        reg = int2binary(int(word[1]), 3, False)
        return reg
    raise ValueError('expect a register but get %s' % word)


def calc_imm(imm):
    match_obj = re.match(imm_pattern, imm)
    if match_obj:
        if match_obj.group(1):
            ret = int(match_obj.group(1), 16)
        else:
            ret = int(match_obj.group(2), 10)
    else:
        raise ValueError('expect a immediate value but get %s' % imm)
    return ret


def int2binary(num, length, signed=True):
    ret = ''
    if signed and (num < -(2 ** (length - 1)) or num >= 2 ** (length - 1)):
        raise ValueError("%d can't be represented as a signed number in %d bits" % (num, length))
    if not signed and num >= 2 ** length:
        raise ValueError("%d can't be represented as a unsigned number in %d bits" % (num, length))
    for i in range(0, length):
        ret = str(num & 1) + ret
        num >>= 1
    return ret


def calc_address(word):
    """
    calculate the address represented by word
    :param word: either an immediate, a label or label[+-]num
    :return: address
    """
    try:
        if is_label(word):
            return symbol_table[word]
        match_obj = re.match(expr_pattern, word)
        if match_obj:
            offset = calc_imm(match_obj.group(3)) * (1 if match_obj.group(2) == '+' else -1)
            return symbol_table[match_obj.group(1)] + offset
    except KeyError:
        raise ValueError('undefined label "%s"' % word)
    return calc_imm(word)


def calc_offset(label):
    try:
        offset = calc_imm(label)
    except ValueError:
        try:
            offset = calc_address(label) - pc
        except ValueError:
            raise ValueError("%s isn't a valid label or an immediate", label)
    return offset


def split(line):
    return re.findall(word_pattern, line)


def remove_comment(lines):
    """
    remove lc3 comment in lines
    :param lines: iterable of string
    :return:
    """
    for line in lines:
        index = line.find(';')
        yield line[:index]


def parse(filename):
    """
    parse the file and establish the symbol table
    :param filename: name of file
    :return: pure instructions
    """
    global orig_address

    with open(filename, 'r') as infile:
        lines = iter(infile.readline, '')
        lines = enumerate(remove_comment(lines), start=1)
        lines = ((index, line.strip()) for index, line in lines if line.strip())
        cur_address = 0
        instrs = []
        first_line = True

        for index, line in lines:

            words = split(line)
            words = [word.upper()
                     if is_keyword(word.upper())
                     else word
                     for word in words]

            if is_label(words[0]):
                symbol_table[words[0]] = cur_address + orig_address
                words.pop(0)

            if words:
                op = words[0]

                if first_line:
                    if op != '.ORIG':
                        raise ValueError('LINE %d: expect .ORIG but not found', index)
                    try:
                        orig_address = calc_imm(words[1])
                    except ValueError as e:
                        raise ValueError('LINE %d: ' % index + str(e))
                    instrs.append((index, words))
                    first_line = False

                if op in op_asm or re.match(br_pattern, op):
                    cur_address = cur_address + 1
                    instrs.append((index, words))

                elif op in pseudo_asm:
                    if op == '.FILL':
                        cur_address = cur_address + 1
                        instrs.append((index, words))
                    elif op == '.BLKW':
                        try:
                            cur_address = cur_address + calc_imm(words[1])
                        except ValueError as e:
                            raise ValueError('LINE %d: ' % index + str(e))
                        instrs.append((index, words))
                    elif op == '.STRINGZ':
                        try:
                            words[1] = ast.literal_eval(words[1])
                            if not isinstance(words[1], str):
                                raise ValueError
                        except Exception:
                            raise ValueError('LINE %d: %s not a legal string' % (index, words[1]))
                        cur_address = cur_address + len(words[1]) + 1
                        instrs.append((index, words))
                    elif op == '.END':
                        return instrs

                else:
                    raise ValueError('LINE %d: expect op_asm or pseudo_asm but get %s' % (index, line))

        raise ValueError('expect .END but not found')


def pass2(instrs):
    """
    :return: list of machine code packed as short
    """
    global pc
    codes = []

    for index, words in instrs:
        # note, .ORIG is at the start of file
        pc = len(codes) + orig_address
        try:
            codes += assemble(words)
        except ValueError as e:
            raise ValueError('LINE %d: ' % index + e.args[0])
    return codes


def main():
    parser = argparse.ArgumentParser(description='Assemble lc3 assembly into machine language')
    parser.add_argument('infile', metavar='*.asm')
    parser.add_argument('-o', required=True, dest='outfile')
    args = parser.parse_args()

    try:
        instrs = parse(args.infile)
        codes = pass2(instrs)

        outfile = args.outfile
        if not outfile.endswith('.obj'):
            outfile += '.obj'

        with open(outfile, 'wb') as out:
            out.write(b''.join(codes))

    except Exception as e:
        print(e)


if __name__ == '__main__':
    main()

