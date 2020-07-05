import re
import io
import bisect

from xml.dom import minidom
from collections import defaultdict

class base(object):
    def __truediv__(self, other):
        return list(map(node, self.xml.getElementsByTagName(other)))
        
    def __or__(self, other):
        li = self/other
        if len(li) != 1:
            raise ValueError("%s has %d childNodes of type %s" % (self, len(li), other))
        return li[0]

class node(base):
    
    def __init__(self, xmlnode):
        self.xml = xmlnode        
        
    def tags(self):    
        return dict(map(lambda t: (t.name, t.value), self/"tag"))

    def attributes(self):
        return dict((k, getattr(self, k)) for k in self.xml.attributes.keys())
        
    def __getattr__(self, k):
        di = (self.xml.attributes or {})
        attr = di.get(k, di.get('xmi:'+k))
        if attr: return attr.value
        else:
            if '_' in k:
                return self.__getattr__(k.replace("_", ":"))
            else:
                return None

    def __repr__(self):
        out = io.StringIO()
        self.xml.writexml(out)
        return re.sub(r"^\s+", "", out.getvalue(), flags=re.MULTILINE).split("\n")[0]
        

class doc(base):
    """
    A helper class for easily navigating the DOM.
    
    Examples:
    
    doc/"connector" list of elements with connector tagName
    doc|"start" same as above but single element (this is asserted)
    doc.by_tag_and_type["element"]["uml:DataType"]
    doc.by_id[...] single element by xml:id
    
    """
    
    def __init__(self, fn):
        self.xml = minidom.parse(fn)
        self.text = open(fn).read()
        self.linebreaks = [m.span()[0] for m in re.finditer(r'\n', self.text)]
        self.by_type = defaultdict(list)
        self.by_tag_and_type = defaultdict(lambda: defaultdict(list))
        self.by_id = dict()
        
        def visit(n, *fns):
            if n.nodeType == n.ELEMENT_NODE:
                for fn in fns:
                    fn(n)
            for c in n.childNodes:
                if c.nodeType == c.ELEMENT_NODE:
                    visit(c, *fns)
                
        def register_by_xmi_type(n):
            n = node(n)
            t = n.type
            if t: self.by_type[t].append(n)
            
        def register_by_tag_and_xmi_type(n):
            n = node(n)
            t = n.type
            if t: self.by_tag_and_type[n.xml.tagName][t].append(n)
            
        def register_by_xmi_id(n):
            n = node(n)
            t = n.xmi_id
            if t and t not in self.by_id:
                # note that duplicate xmi:ids do exist e.g. for generalizations
                self.by_id[t] = n

        visit(self.xml, 
            register_by_xmi_type,
            register_by_xmi_id,
            register_by_tag_and_xmi_type)
    
    def locate(self, node):
        pat = r'(?<=<)(%s[^\\/]*?xmi:idref="%s"[^\\/]*?)((?= \\/>)|(?=>))' % (node.xml.tagName, node.idref)
        offset = next(re.finditer(pat, self.text)).span()[0]
        line_no = bisect.bisect_left(self.linebreaks, offset)
        char = self.linebreaks[line_no] - offset
        line_no += 1
        return (line_no, char)