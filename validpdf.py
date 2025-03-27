"""
VALIDAÇÃO:
[OK ou ERRO] Estrutura geral
[OK ou ERRO] Sintaxe de objetos
[OK ou ERRO] Referências
[OK ou ERRO] Tabela xref
[Detalhes de erros, se houver]

ESTATÍSTICAS:
Total de objetos: X
Objetos por tipo: Catalog=1, Pages=1, Page=Y, Font=Z, ...
Total de páginas: Y
Tamanho do documento: W bytes
Overhead estrutural: V bytes (P%)

CONTEÚDO:
Título: [título do documento]
Autor: [autor do documento]
Data de criação: [data]
Texto extraído: [primeiros 200 caracteres...]

ÁRVORE DE OBJETOS:
1: Catalog
  +- 2: Pages
    +- 3: Page
    +- 4: Font
    +- 5: Contents (stream)
6: Metadata

ANÁLISE AVANÇADA:
[Resultados de análises específicas definidas no arquivo de configuração]
"""

extrair_texto = None
gerar_sumario = None
detectar_ciclos = None
nivel_detalhe = None
validar_xref = None

from exemplos.exemplosimples import *

print(extrair_texto)
print(gerar_sumario)
print(detectar_ciclos)
print(nivel_detalhe)
print(validar_xref)


def read_pdf(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()
    return text


FILE = read_pdf('exemplos/exemplo3.pdf')

FILE_SIZE = len(FILE)


def check_header(file):
    return file.startswith('%SPDF-') or file.startswith('%PDF-')


print(check_header(FILE))


def get_startbody(file):
    for i in range(256):
        if file[i] == '\n':  # get the second line
            return i + 1


STARTBODY = get_startbody(FILE)


def check_eof(file):
    return file.endswith('%%EOF')


print(check_eof(FILE))


def get_startxref(file, filesize):
    end = filesize - 6  # ignoring this '\n%%EOF'
    for i in range(end - 1, 0, -1):
        if file[i] == '\n':  # get only one line
            return int(file[i + 1:end])


STARTXREF = get_startxref(FILE, FILE_SIZE)

BODY = FILE[STARTBODY:STARTXREF]

BODY_SIZE = len(BODY)

STARTXREF_KEYWORD_OFFSET = FILE_SIZE - 6 - len(str(STARTXREF)) - 10  # f'startxref\n{xref_address}\n%%EOF'


def get_starttrailer(file, startxref, startxref_keyword_offset):
    end = startxref_keyword_offset  # ignoring this f'startxref\n{xref_address}\n%%EOF'
    for i in range(startxref, end):
        if file[i] == 't':  # trailler
            return i


STARTTRAILER = get_starttrailer(FILE, STARTXREF, STARTXREF_KEYWORD_OFFSET)

XREF = FILE[STARTXREF:STARTTRAILER]

# Trailler is  'trailer << <trailer key–value pair>+ >> startxref <cross-reference table start address> %%EOF'
# but i am only considering 'trailer << <trailer key–value pair>+ >> '
TRAILER = FILE[STARTTRAILER:STARTXREF_KEYWORD_OFFSET]


def string_to_dict(dict_str):
    tokens = dict_str.split()
    return tokens_to_dict(tokens)


def tokens_to_dict(tokens, index=-1, index_return=False):
    data = {}
    key = None
    value = []
    i = index
    while i < len(tokens):
        i += 1
        token = tokens[i]

        if token == '<<':
            if key:
                data[key], i = tokens_to_dict(tokens, i, True)
            key = None
            value = []
        elif token == '>>' or token == 'endobj':
            if len(value) == 1:
                value = value[0]  # ['7'] => '7'
            if key:
                data[key] = value
            break
        elif token.startswith('/'):
            if key:
                if value:
                    if len(value) == 1:
                        value = value[0]  # ['7'] => '7'
                    data[key] = value
                    key = None
                    value = []
                else:
                    value = token
                    data[key] = value  # '/Type': '/Pages'
                    key = None
                    value = []
                    continue
            key = token
            value = []
        else:
            if not key:
                continue
            value.append(token)

    if index_return:
        return data, i
    return data


TRAILER_DICT = string_to_dict(TRAILER)


def check_trailer(trailer_dict):
    required_tags = ['/Size', '/Root']
    # tags = ['/Info','/Prev']
    for tag in required_tags:
        if tag not in trailer_dict:
            return False

    return True


print(check_trailer(TRAILER_DICT))

TRAILER_SIZE = int(TRAILER_DICT['/Size'])

TRAILER_ROOT = TRAILER_DICT['/Root']


def xref_to_list(xref):
    lines = xref.split('\n')
    lines = [line.split() for line in lines if line]

    first = int(lines[1][0])
    qtd = int(lines[1][1])

    lines = lines[2:]  # removing 'xref' and '0 7', 2 first lines

    sections = []
    objects = [[first, qtd]]

    for line in lines:
        if len(line) == 2:
            sections.append(objects)
            first = int(line[0])
            qtd = int(line[1])
            objects = [[first, qtd]]
            continue

        line[0] = int(line[0])
        line[1] = int(line[1])
        objects.append(line)

    if objects:
        sections.append(objects)

    return sections


XREF_LIST = xref_to_list(XREF)


def check_xref_size(xref_list, trailer_size):
    size = 0
    for section in xref_list:
        info = section[0]
        first = info[0]
        qtd = info[1]
        section_size = len(section[1:])

        if qtd != section_size:
            return False

        size += section_size

    if size != trailer_size:
        return False

    return True


print(check_xref_size(XREF_LIST, TRAILER_SIZE))


# f = object_id gen_num f
# n = byte_offset gen_num n

def get_xref_addresses(xref_list):
    xref_addresses = {}
    for section in xref_list:
        info = section[0]
        first = info[0]
        qtd = info[1]

        section = section[1:]  # ignoring info, first element

        for i in range(qtd):
            obj = section[i]

            if obj[2] == 'f':
                continue  # ignoring validation on 'f'

            byte_offset = obj[0]

            xref_addresses[first + i] = byte_offset

    return xref_addresses


XREF_ADDRESSES = get_xref_addresses(XREF_LIST)


def check_xref_addresses(xref_addresses, body, start_body=10):  # start_body=10 for spdf header
    for obj_id, address in xref_addresses.items():

        if body[address - start_body] != str(obj_id):
            return False

    return True


print(check_xref_addresses(XREF_ADDRESSES, BODY, STARTBODY))

OBJECTS = {1: {}}


def update_xref_addresses(objects, xref_addresses, start_body=10):  # start_body=10 for spdf header)
    for obj_id, address in xref_addresses.items():
        if obj_id not in objects:
            objects[obj_id] = {}
        objects[obj_id]['address'] = address - start_body


update_xref_addresses(OBJECTS, XREF_ADDRESSES)


def update_contents(objects, body, body_size):
    for obj_id, obj in objects.items():
        address = obj['address']
        i = address

        while (i < body_size):
            if body[i:i + 6] == 'endobj':
                break
            i += 1

        obj['content'] = body[address:i + 6]


update_contents(OBJECTS, BODY, BODY_SIZE)


def remove_comments(objects):
    for obj_id, obj in objects.items():
        content = obj['content']
        new_content = ''
        start_comment = False

        for i in range(len(content)):
            if start_comment:
                if content[i] == '\n':
                    new_content += '\n'
                    start_comment = None
                    continue
            elif content[i] == '%':
                start_comment = True
                continue
            else:
                new_content += content[i]

        obj['content'] = new_content


remove_comments(OBJECTS)


def get_reference_id(tokens):
    ids = []
    for i in range(len(tokens)):
        token = tokens[i]
        if token == 'R':
            ref_id = tokens[i - 2]
            ref_id = int(ref_id)
            ids.append(ref_id)

    return ids


def check_references(objects):
    for obj in objects.values():
        content = obj['content']
        tokens = content.split()

        refs = get_reference_id(tokens)
        for id in refs:
            if id not in objects:
                return False

    return True


print(check_references(OBJECTS))


def get_dictionaries(objects):
    for obj in objects.values():
        obj['dictionary'] = string_to_dict(obj['content'])


get_dictionaries(OBJECTS)


class Node:
    def __init__(self, info=''):
        self.info = info
        self.children = []

    def __str__(self):
        return self.info

    def add_child(self, child):
        self.children.append(child)
        return True

    def height(self):
        if not self.children:
            return 1
        return 1 + max([child.height() for child in self.children])

    def find_node(self, target):
        if self.info == target:
            return self

        for child in self.children:
            if child.info == target:
                return child
            found = child.find_node(target)
            if found:
                return found

    def print(self, level=0):
        result = "\t" * level + str(self) + "\n"
        for child in self.children:
            result += child.print(level + 1)
        return result


class Tree:
    def __init__(self, root=None):
        if root and not isinstance(root, Node):
            root = Node(root)
        self.root = root

    def __str__(self):
        return self.print()

    def is_empty(self):
        return self.root is None

    def height(self):
        return self.root.height()

    def find_node(self, target):
        if self.is_empty():
            return None
        return self.root.find_node(target)

    def add_child(self, target, node):
        if self.is_empty():
            return None

        if not isinstance(target, Node):
            target = self.find_node(target)

        if not isinstance(node, Node):
            node = Node(node)

        return target.add_child(node)

    def print(self):
        if self.is_empty():
            return ''
        return self.root.print()


def references_recursive(object):
    references = []
    if 'dictionary' in object:
        object = object['dictionary']
    for key, value in object.items():
        if key == '/Parent':
            continue
        if isinstance(value, dict):
            references += references_recursive(value)
            continue
        references += get_reference_id(value)

    return references


def get_tree(objects, root):
    root_object = objects[root]
    root = f"{root}: {root_object['dictionary'].get('/Type', 'obj')}"
    tree = Tree(root)

    references = references_recursive(root_object)

    for ref_id in references:
        node = get_tree(objects, ref_id).root
        tree.add_child(root, node)

    return tree


tree = get_tree(OBJECTS, get_reference_id(TRAILER_ROOT)[0])

print(tree)






