import os
import argparse
import zipfile

from lxml import etree, objectify
from filehash import FileHash

sha256 = FileHash('sha256')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'directory', help='The directory where the mod is located')

    args = parser.parse_args()

    mod_files = get_files(args.directory)
    mod_context = get_context(args.directory)
    create_catalog(mod_context, mod_files, args.directory)
    create_zip(mod_context, args.directory)


def get_files(directory):
    list_of_files = []

    exclude_prefixes = ('__', '.')
    exclude_suffix = ('.cat', '.dat')
    for root, dirs, files in os.walk(directory):
        dirs[:] = [dir for dir in dirs if not dir.startswith(exclude_prefixes)]
        list_of_files.extend([os.path.join(root, file) for file in files
                              if not file.endswith(exclude_suffix)
                              and not file.startswith('content.xml')])

    return list_of_files


def get_context(directory):
    context_tree = objectify.parse(os.path.join(directory, 'content.xml'))
    return context_tree.getroot().attrib


def create_catalog(context, files, directory):
    mod_id = context.get('id')
    with open(os.path.join(directory, mod_id) + '.cat', 'w') as cat, open(os.path.join(directory, mod_id) + '.dat', 'wb') as dat:
        for file in files:
            with open(file, 'rb') as source:
                stats = os.stat(file)
                hash = sha256.hash_file(file)
                cat.write("%s %s %s %s\n" %
                          (os.path.relpath(file, directory), int(stats.st_size), int(stats.st_mtime), hash))
                dat.write(source.read())


def create_zip(context, directory):
    mod_id = context.get('id')
    cat_name =  mod_id + '.cat'
    dat_name = mod_id + '.dat'
    content_xml = 'content.xml'
    with zipfile.ZipFile(os.path.join(directory, mod_id) + '.zip', 'w') as zf:
        zf.write(os.path.join(directory, content_xml), content_xml, compress_type = zipfile.ZIP_DEFLATED)
        zf.write(os.path.join(directory, cat_name), cat_name, compress_type = zipfile.ZIP_DEFLATED)
        zf.write(os.path.join(directory,dat_name), dat_name, compress_type = zipfile.ZIP_DEFLATED)


main()
