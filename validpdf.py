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

from Tree import Tree

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


class PDFValidador:
    def __init__(self, file_path):
        self.file_path = file_path
        self.file = self.read_pdf()
        self.filesize = len(self.file)

        print(self.check_header())

        self.startbody = self.get_startbody()  # startbody=10 for spdf header

        print(self.check_eof())

        self.startxref = self.get_startxref()

        self.body = self.file[self.startbody:self.startxref]
        self.bodysize = len(self.body)

        self.startxref_keyword_offset = self.filesize - 6 - len(str(self.startxref)) - 10  # f'startxref\n{xref_address}\n%%EOF'

        self.starttrailer = self.get_starttrailer()

        self.xref = self.file[self.startxref:self.starttrailer]
        print(self.xref)

        # Trailler is  'trailer << <trailer key–value pair>+ >> startxref <cross-reference table start address> %%EOF'
        # but i am only considering 'trailer << <trailer key–value pair>+ >> '
        self.trailer = self.file[self.starttrailer:self.startxref_keyword_offset]

        self.trailer_dict = self.string_to_dict(self.trailer)
        print(self.check_trailer(self.trailer_dict))

        self.trailer_size = int(self.trailer_dict['/Size'])
        self.trailer_root = self.trailer_dict['/Root']

        self.xref_list = self.xref_to_list()
        print(self.check_xref_size())

        self.xref_addresses = self.get_xref_addresses()
        print(self.check_xref_addresses())

        self.objects = {1: {}}
        self.update_xref_addresses()
        self.update_contents()
        self.remove_comments()

        print(self.check_references())

        self.get_dictionaries()

        self.tree = self.get_tree(self.objects, self.get_reference_id(self.trailer_root)[0])
        print(self.tree)

    def read_pdf(self):
        with open(self.file_path, "r", encoding="utf-8") as file:
            text = file.read()
        return text

    def check_header(self):
        return self.file.startswith('%SPDF-') or self.file.startswith('%PDF-')

    def get_startbody(self):
        for i in range(256):
            if self.file[i] == '\n':  # get the second line
                return i + 1

    def check_eof(self):
        return self.file.endswith('%%EOF')

    def get_startxref(self):
        end = self.filesize - 6  # ignoring this '\n%%EOF'
        for i in range(end - 1, 0, -1):
            if self.file[i] == '\n':  # get only one line
                return int(self.file[i + 1:end])

    def get_starttrailer(self):
        end = self.startxref_keyword_offset  # ignoring this f'startxref\n{xref_address}\n%%EOF'
        for i in range(self.startxref, end):
            if self.file[i] == 't':  # trailler
                return i

    def tokens_to_dict(self, tokens, index=-1, index_return=False):
        data = {}
        key = None
        value = []
        i = index
        while i < len(tokens):
            i += 1
            token = tokens[i]

            if token == '<<':
                if key:
                    data[key], i = self.tokens_to_dict(tokens, i, True)
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

    def string_to_dict(self, dict_str):
        tokens = dict_str.split()
        return self.tokens_to_dict(tokens)

    def check_trailer(self, trailer_dict):
        required_tags = ['/Size', '/Root']
        # tags = ['/Info','/Prev']
        for tag in required_tags:
            if tag not in trailer_dict:
                return False

        return True

    def xref_to_list(self):
        lines = self.xref.split('\n')
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

    def check_xref_size(self):
        size = 0
        for section in self.xref_list:
            info = section[0]
            first = info[0]
            qtd = info[1]
            section_size = len(section[1:])

            if qtd != section_size:
                return False

            size += section_size

        if size != self.trailer_size:
            return False

        return True

    def get_xref_addresses(self):
        # f = object_id gen_num f
        # n = byte_offset gen_num n
        xref_addresses = {}
        for section in self.xref_list:
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

    def check_xref_addresses(self):
        for obj_id, address in self.xref_addresses.items():

            if self.body[address - self.startbody] != str(obj_id):
                return False

        return True

    def update_xref_addresses(self):
        for obj_id, address in self.xref_addresses.items():
            if obj_id not in self.objects:
                self.objects[obj_id] = {}
            self.objects[obj_id]['address'] = address - self.startbody

    def update_contents(self):
        for obj_id, obj in self.objects.items():
            address = obj['address']
            i = address

            while i < self.bodysize:
                if self.body[i:i + 6] == 'endobj':
                    break
                i += 1

            obj['content'] = self.body[address:i + 6]

    def remove_comments(self):
        for obj_id, obj in self.objects.items():
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

    def get_reference_id(self, tokens):
        ids = []
        for i in range(len(tokens)):
            token = tokens[i]
            if token == 'R':
                ref_id = tokens[i - 2]
                if not ref_id.isdigit():
                    continue
                ref_id = int(ref_id)
                ids.append(ref_id)

        return ids

    def check_references(self):
        for obj in self.objects.values():
            content = obj['content']
            tokens = content.split()

            refs = self.get_reference_id(tokens)
            for id in refs:
                if id not in self.objects:
                    return False

        return True

    def get_dictionaries(self):
        for obj in self.objects.values():
            obj['dictionary'] = self.string_to_dict(obj['content'])

    def references_recursive(self, object):
        references = []
        if 'dictionary' in object:
            object = object['dictionary']
        for key, value in object.items():
            if key == '/Parent':
                continue
            if isinstance(value, dict):
                references += self.references_recursive(value)
                continue
            references += self.get_reference_id(value)

        return references

    def get_tree(self, objects, root):
        root_object = objects[root]
        root = f"{root}: {root_object['dictionary'].get('/Type', 'obj')}"
        tree = Tree(root)

        references = self.references_recursive(root_object)

        for ref_id in references:
            node = self.get_tree(objects, ref_id).root
            tree.add_child(root, node)

        return tree


pdf3 = PDFValidador('exemplos/exemplo3.pdf')
pdf4 = PDFValidador('exemplos/exemplo4.pdf')
pdf5 = PDFValidador('exemplos/exemplo5.pdf')

pdf5



