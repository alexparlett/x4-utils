import argparse
import os

from lxml import etree, objectify
from dictdiffer import diff
from dictdiffer.utils import dot_lookup
from copy import deepcopy

unique_attrib = [
    'id',
    'name',
    'value',
    'cue',
    'command',
    'ref'
]

excluded_attrib = [
    '{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation'
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'left', help='The original file')
    parser.add_argument(
        'right', help='The changed file')
    parser.add_argument('--out', help='The output file', default='patch.xml')

    args = parser.parse_args()

    parser = objectify.makeparser()
    lTree = objectify.parse(args.left, parser)
    rTree = objectify.parse(args.right, parser)

    lDict, rDict = compare(lTree, rTree)
    differences = find_differences(lDict, rDict)
    patch(differences, lTree, rTree, lDict, rDict, args.out)


def compare(left, right):
    lRoot = left.getroot()
    rRoot = right.getroot()

    lDict = {}
    rDict = {}

    parse_children(lRoot, left, lDict)
    parse_children(rRoot, right, rDict)

    identical = lDict == rDict

    if identical:
        print('Files identical')
        os.sys.exit()

    return lDict, rDict


def parse_children(element, tree, xpath):
    if 'comment' in element.tag:
        return

    path = better_xpath(element,tree)
    entry = {
        'tag': element.tag,
        'attrib': {key: value for (key, value) in element.attrib.items() if key not in excluded_attrib},
        'text': element.text,
        'path': path,
        'children': {}
    }

    xpath[path] = entry
    for child in element.getchildren():
        parse_children(child, tree, entry['children'])


def find_differences(left, right):
    return list(diff(left, right, ignore=set(['path'])))


def patch(differences, lTree, rTree, lDict, rDict, out):

    root = etree.Element('diff')

    for difference in differences:
        type = difference[0]
        path = difference[1]
        change = difference[2]

        if type == 'change':
            if 'attrib' in path:
                split = path.split('.attrib.')
                parent_path = path.split('.attrib.')[0]
                attrib = path.split('.attrib.')[1]
                lnode = dot_lookup(lDict, parent_path)
                replace = etree.SubElement(root, 'replace', attrib={ 'sel': lnode['path'] + '/@' + attrib})
                replace.text = change[1]
            else:
                lnode = dot_lookup(lDict, path, parent=True)
                replace = etree.SubElement(root, 'replace', attrib={ 'sel': lnode['path'] + '/text()'})
                replace.text = change[1]
        elif type == 'add':
            if 'attrib' in path:
                for c in change: 
                    lnode = dot_lookup(lDict, path, parent=True)
                    add = etree.SubElement(root, 'add', attrib={ 'sel': lnode['path'], 'type': '@' + c[0]})
                    add.text = c[1]
            else: 
                for c in change: 
                    xpath = c[0]
                    relement = rTree.xpath(xpath)[0]
                    lelement = relement.getprevious()
                    if lelement is not None:
                        xpath = better_xpath(lelement, rTree)
                        add = etree.SubElement(root, 'add', attrib={ 'sel': xpath, 'pos': 'after'})
                        add.insert(0, deepcopy(relement))
                    else:
                        lelement = relement.getparent()
                        xpath = better_xpath(lelement, rTree)
                        add = etree.SubElement(root, 'add', attrib={ 'sel': xpath, 'pos': 'prepend'})
                        add.insert(0, deepcopy(relement))
        elif type == 'remove':
            if 'attrib' in path:
                for c in change: 
                    lnode = dot_lookup(lDict, path, parent=True)
                    remove = etree.SubElement(root, 'remove', attrib={ 'sel': lnode['path'] + '/@' + c[0]})
            else:
                for c in change: 
                    xpath = c[0]
                    etree.SubElement(root, 'remove', attrib={ 'sel': xpath})

    et = etree.ElementTree(root)
    et.write(out, xml_declaration=True, encoding='utf-8', pretty_print=True)


def better_xpath(element, etree):
    xpath = xpath_for_element(element, etree)

    epath = element.getparent()
    while epath is not None:
        xpath = xpath_for_element(epath, etree) + xpath
        epath = epath.getparent()

    return xpath

def xpath_for_element(element, etree):
    xpath ='/' + element.tag

    if element.tag == 'comment':
        xpath += '()'

    if not element.attrib or not (any(key in element.attrib for key in unique_attrib)):
        foundSiblingElement = len(element.getparent().xpath(element.tag)) > 1
        if foundSiblingElement:
            idx = 1
            prev = element.getprevious()
            while prev is not None:
                if prev.tag == element.tag:
                    idx += 1
                prev = prev.getprevious()
            xpath += '[' + str(idx) + ']'
    else:
        attribs = [{'key': key, 'value': value} for key,value in element.items() if key in unique_attrib]
        xpath += '[@' + attribs[0]['key'] + '=\'' + attribs[0]['value'] + '\']'
      
    return xpath


main()
