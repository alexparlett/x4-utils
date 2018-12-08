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
    path = better_xpath(element,tree)
    entry = {
        'tag': element.tag,
        'attrib': element.attrib,
        'text': element.text,
        'children': {}
    }

    for child in element.getchildren():
        parse_children(child, tree, entry['children'])

    xpath[path] = entry


def find_differences(left, right):
    return list(diff(left, right))


def patch(differences, lTree, rTree, lDict, rDict, out):

    root = etree.Element('diff')

    for difference in differences:
        type = difference[0]
        path = difference[1]
        change = difference[2]

        if type == 'change':
            lnode = dot_lookup(lDict, path, parent=True)
            if path.endswith('attrib'):
                ac = dict(change[1].items() - change[0].items())
                rm = dict(change[0].items() - change[1].items())
                for key, value in ac.items():
                    if key in change[0]:
                        replace = etree.SubElement(root, 'replace', attrib={ 'sel': lnode['path'] + '/@' + key})
                        replace.text = value.strip()
                    else:
                        add = etree.SubElement(root, 'add', attrib={ 'sel': lnode['path'], 'type': '@' + key})
                        add.text = value.strip()
                for key, value in rm.items():
                    if key not in change[1]:
                         etree.SubElement(root, 'remove', attrib={ 'sel': lnode['path'] + '/@' + key})
            else:
                replace = etree.SubElement(root, 'replace', attrib={ 'sel': lnode['path'] + '/text()'})
                replace.text = change[1].strip()
        elif type == 'add':
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
