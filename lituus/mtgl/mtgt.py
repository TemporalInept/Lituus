#!/usr/bin/env python
""" mtgt.py
Copyright (C) 2019  Temporal Inept (temporalinept@mail.com)

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

MTG (Language) Tree
"""

__name__ = 'mtgt'
__license__ = 'GPLv3'
__version__ = '0.0.2'
__date__ = 'August 2019'
__author__ = 'Temporal Inept'
__maintainer__ = 'Temporal Inept'
__email__ = 'temporalinept@mail.com'
__status__ = 'Development'

import networkx as nx
from networkx.classes.ordered import OrderedDiGraph as Tree

class MTGTException(Exception):
    def __init__(self,message): Exception.__init__(self,message)

#### PRINT SYMBOLS
# root, no symbol
SYM_CHILD      = '├'
SYM_2ND_ORDER  = '│'
SYM_LAST_CHILD = '└'
SYM_BRANCH     = '─'

class MTGTree:
    """
     A ordered, rooted directed acyclic graph (DAG) using networkx's OrderedDiGraph
     The ParseTree has one and only one root node identified as 'root' which has no
     attributes and 0 or more subnodes. Each subnode in the tree is identified by a
     one-up serial identifier of the form node-type:n and uses networkx's attr
     parameter of the add_node function to define the data dictionary for the given
     node. Every node (except root) can have 0 or more user defined attributes but
     our intent is that only leaf nodes will have ddefined attributes.

     Because the tree is an ordered, rooted DAG (1) there is a unique root or
     source node, (2) each node has one and only one parent (but a parent can
     have 0 or more children) and (3) there is no path from a given node that
     will eventually lead back to that node. Because the DAG is ordered, (4) the
     order in which nodes are added to a 'parent' matter: the first node added
     to a parent will be the 'leftmost' child and the last node added to a parent
     will be the 'rightmost' child. These properties provide the basis of a parse
     tree but are not strictly enforced. However, they are maintained by using
     only the functions provided by the class definition vice the networkx object
     directly.
    """
    def __init__(self,tree=None):
        """
         Creates an empty null tree unless tree is definied
        :param tree: a networkx.OrderedDiGraph
        """
        if tree is None:
            self._t = Tree()         # an empty null tree
            self._ns = {}            # node-id dictionary
            self._t.add_node('root') # add the root node
        else:
            self._t = tree
            self._ns = {}
            for node in self._t.nodes:
                # NOTE: not an efficient way to do this
                try:
                    k,v = node.split(':')
                    v = int(v)
                    if k in self._ns:
                        if v+1 > self._ns[k]: self._ns[k] = v + 1
                    else: self._ns[k] = v
                except ValueError:
                    # the root node or there is an error in the node-ids
                    if node != 'root':
                        raise MTGTException('Invalid node-id: {}'.format(node))

    def print(self,show_attr=False):
        """
         prints the tree with each branch indented 2 spaces from parent.
         :param show_attr: if set will shows the attributes as well
        """
        # get the depths of the node from the 'root', then traverse the tree in
        # preorder (left to right) printing each node spacing by depth
        ds = nx.shortest_path_length(self._t,'root')
        for n in nx.dfs_preorder_nodes(self._t,'root'):
            if not show_attr: print("{}{}".format(" " * ds[n],n))
            else:
                attrs = ["{}={}".format(k,v) for k,v in self._t.node[n].items()]
                if attrs: print("{}{} ({})".format(" " * ds[n],n," ".join(attrs)))
                else: print("{}{}".format(" " * ds[n],n))

    def print2(self,show_attr=False):
        """
         prints the tree with each branch indented 2 spaces from parent.
         :param show_attr: if set will shows the attributes as well
        """
        # get the depths of the node from the 'root', then traverse the tree in
        # preorder (left to right) printing each node spacing by depth
        cs = self.children('root')
        lastchild = cs[-1]

        ds = nx.shortest_path_length(self._t, 'root')
        for nid in nx.dfs_preorder_nodes(self._t,'root'):
            if nid == 'root':
                print("<root>")
                continue

            # determine what the leftmost symbol will be
            rsym = ''
            msym = " " * ds[nid]
            if nid in cs:
                # direct descendant of root
                if nid == lastchild: lsym = SYM_LAST_CHILD
                else: lsym = SYM_CHILD
            else:
                # leftmost symbol will be a vertical line unless the last
                # child of root is a descendant of this node
                if lastchild in self.ancestors(nid): lsym = ' '
                else: lsym = SYM_2ND_ORDER

                # if the parent of this node has siblings and it is not
                # the last child change the mid symbols
                pid = self.parent(nid)
                ss = self.children(self.parent(pid))
                if self.siblings(pid) and pid != ss[-1]:
                    msym = list(msym)
                    msym[-1] = SYM_2ND_ORDER
                    msym = "".join(msym)

                # determine what the rightmost symbol will be
                ss = self.children(self.parent(nid)) # get all nodes on same level
                if nid == ss[-1]: rsym = SYM_LAST_CHILD
                else: rsym = SYM_CHILD

            # attributes?
            attrs = ''
            if show_attr:
                ps1 = ["{}={}".format(k,v) for k,v in self._t.node[nid].items()]
                if ps1: attrs = "({})".format(" ".join(ps1))

            print("{}{}{}{}{}".format(lsym,msym,rsym,nid,attrs))

    @property # return the root node-id (which should always be 'root')
    def root(self): return next(nx.topological_sort(self._t))

    @property # return the underlying networkx tree
    def tree(self): return self._t

    """ returns whether tree has node with id nid """
    def has_node(self,nid): return nid in self._t.node

    """ returns the node with id nid's data dict """
    def node(self,nid):
        try:
            return self._t.node[nid]
        except KeyError:
            raise MTGTException("No such node {}".format(nid))

    """ returns a list of all node ids in depth-first order """
    def nodes(self): return [n for n in nx.dfs_preorder_nodes(self._t,'root')]

    """ returns the value of the attribute attr of the node with id nid"""
    def attr(self,nid,attr):
        try:
            return self._t.node[nid][attr]
        except KeyError:
            if not nid in self._t:
                raise MTGTException("No such node {}".format(nid))
            else:
                raise MTGTException("No such attribute {}".format(nid))

    """ returns whether the node with id nid is a leaf """
    def is_leaf(self,nid):
        try:
            return self._t.out_degree[nid] == 0
        except KeyError:
            raise MTGTException("No such node {}".format(nid))

    """ returns the parent id of the node with id nid """
    def parent(self,nid):
        try:
            return next(self._t.predecessors(nid))
        except StopIteration:
            return None
        except KeyError:
            raise MTGTException("No such node {}".format(nid))

    """ 
     returns the ancestors (ids) of the node with id nid (in no particular order 
    """
    def ancestors(self,nid):
        try:
            return [n for n in nx.ancestors(self._t,nid)]
        except KeyError:
            raise MTGTException("No such node {}".format(nid))

    """ returns the children of the node with id nid """
    def children(self,nid):
        try:
            return [n for n in self._t.successors(nid)]
        except KeyError:
            raise MTGTException("No such node {}".format(nid))

    """ returns the siblings of the node with id nid """
    def siblings(self,nid):
        try:
            ss = self.children(self.parent(nid))
            ss.remove(nid)
            return ss
        except KeyError:
            raise MTGTException("No such node {}".format(nid))

    def add_node(self,pid,ntype,**kwargs):
        """
         adds a node of type ntype with attributes kwargs to the tree under
         the node with id pid
        :param pid: parent id
        :param ntype: the type of node
        :param kwargs: attributes
        :return: the node id of the new node
        """
        nid = self._node_id_(ntype)
        self._t.add_node(nid)
        for k,v in kwargs.items(): self._t.node[nid][k] = v
        self._t.add_edge(pid,nid)
        return nid

    def add_node_ur(self,ntype,**kwargs):
        """
         adds a rootless node of type ntype with attributes to the tree
        :param ntype: the type of node
        :param kwargs: attributes
        :return: the node id of the new node
        """
        nid = self._node_id_(ntype)
        self._t.add_node(nid)
        for k, v in kwargs.items(): self._t.node[nid][k] = v
        return nid

    def add_edge(self,pid,cid):
        """
         adds an edge from parent pid to child cid
        :param pid: parent-id
        :param cid: child-id
        """
        # don't allow edges to be added to a node with a parent
        if self.parent(cid): raise MTGTException("{} has a parent".format(cid))
        self._t.add_edge(pid,cid)

    # TODO:
    def del_node(self): pass

    # TODO:
    def del_edge(self): pass

    def add_attr(self,nid,k,v):
        """
         adds the k=v pair to the nodes attributes. Note if the attribute k
         already exists in the node's attributes, it will be overwritten with v
        :param nid: the node-id
        :param k: the key
        :param v: the value
        """
        try:
            self._t.node[nid][k] = v
        except KeyError:
            raise MTGTException("No such node {}".format(nid))

    # TODO:
    def del_attr(self): pass

    def findall(self,ntype,source='root',attr=None,val=None):
        """
         finds all nodes in the tree of the type ntype starting at source with
         attribute attr (if set) having value val (if set)
        :param ntype: node type to find
        :param source: the source to start the search from
        :param attr: the attribute key the node will have
        :param val: the val that the given attribute key will have
        :return: a list of node ids
        """
        if val and not attr: raise MTGTException("Cannot have val without attr")
        found = []
        i = 0
        while True:
            nid = "{}:{}".format(ntype,i)
            if nid in self._t:
                if source in nx.ancestors(self._t,nid):
                    if attr:
                        if attr in self._t.node[nid]:
                            if val:
                                if self._t.node[nid][attr] == val: found.append(nid)
                            else:
                                if attr in self._t.node[nid]: found.append(nid)
                    else: found.append(nid)
                i += 1
            else:
                break
        return found

#### PRIVATE FCTS ####

    def _node_id_(self,ntype):
        """
         returns the next one-up serial number of node type ntype
        :param ntype: the node type being adding
        :return: the new node-id
        """
        if ntype in self._ns:
            nid = "{}:{}".format(ntype,self._ns[ntype])
            self._ns[ntype] += 1
        else:
            nid = "{}:0".format(ntype)
            self._ns[ntype] = 1
        return nid

def fuse_tree(a,b):
    """
     fuses two networkx trees a and b under a single root. Meant for 'merging' two
     trees from two sides of the same card.
      Let A be a subtree of a such that
       root
         A
      and let B be a subtree of b suc that
       root
         B

      the fused tree will be of the form:
      root
        card-half (side=a)
          A
        card-half (side=b)
          B
    :param a: netwokx tree a
    :param b: MTGTree b
    :return: a fused networkx tree
    """
    # TODO: rather inefficient initializing each to MTGTrees but it simplifies
    #  the code
    # initialize the MTGTrees
    tree = MTGTree()
    pid = tree.root
    apid = tree.add_node(pid,'card-half',side='a')
    _fuse_copy_(tree,apid,MTGTree(a),'root')
    bpid = tree.add_node(pid,'card-half',side='b')
    _fuse_copy_(tree,bpid,MTGTree(b),'root')
    return tree.tree

def _fuse_copy_(nt,nid,ot,oid):
    """
     recursive walk and copy of old tree ot at node-id oid to new tree nt at
     node-id nid
    :param nt: the MTGTree object new tree
    :param nid: current node-id in nt
    :param ot: the MTGTree object old tree
    :param oid: current node-id in ot
    """
    # NOTE that oid itself is not copied. This is done intentionally so that
    # root node (in the first call to _fuse_copy_) is not copied
    if not ot.is_leaf(oid):
        for cid in ot.children(oid): # BFS
            lbl = cid.split(':')[0]
            cid1 = nt.add_node(nid,lbl)
            for k,v in ot.node(cid).items(): nt.add_attr(cid1,k,v)
            _fuse_copy_(nt,cid1,ot,cid)