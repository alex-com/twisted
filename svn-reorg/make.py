#!/usr/bin/env python
# Run this script in the toplevel of a brand new svn directory.
# It expects a ../trunk to also exist.

from glob import glob
import os, os.path

def sh(command):
    print "--$", command
    code = os.system(command)
    if code != 0:
        raise Exception("system(%r) returned error code %d" % (command, code))

twisted_subprojects = ["conch", "flow", "lore", "mail", "names",
                       "news", "pair", "runner", "web", "web2",
                       "words", "xish"]

def migrate_subproj(proj):
    pdir = proj
    sh('svn mkdir "%(pdir)s" "%(pdir)s/twisted" "%(pdir)s/twisted/plugins"' % locals())
    sh('svn cp "../trunk/twisted/%(proj)s" "%(pdir)s/twisted/"' % locals())
    sh('svn rm "%(pdir)s/twisted/%(proj)s/topfiles"' % locals())
    for fname in glob("../trunk/twisted/%(proj)s/topfiles/*" % locals()):
        sh('svn cp "%(fname)s" "%(pdir)s/"' % locals())

    sh('svn cp "../trunk/LICENSE" "%(pdir)s/LICENSE"' % locals())
    
    if os.path.exists('../trunk/twisted/plugins/twisted_%(proj)s.py' % locals()):
        sh('svn cp "../trunk/twisted/plugins/twisted_%(proj)s.py" '
           '"%(pdir)s/twisted/plugins/"' % locals())

    if os.path.exists('../trunk/doc/'+proj):
        sh('svn cp "../trunk/doc/%(proj)s" "%(pdir)s/doc"' % locals())
    if os.path.exists('../trunk/bin/'+proj):
        sh('svn cp "../trunk/bin/%(proj)s" "%(pdir)s/bin"' % locals())

def migrate_core():
    proj = "core"
    pdir = proj
    sh('svn mkdir "%(pdir)s" "%(pdir)s/twisted"' % locals())
    dont_copy_top = ['README', 'doc', 'twisted', 'setup.py']
    for fname in glob("../trunk/*"):
        if os.path.basename(fname) not in dont_copy_top:
            sh('svn cp "%(fname)s" "%(pdir)s/"' % locals())
            
    dont_copy_twisted = twisted_subprojects + ['topfiles']
    for fname in glob("../trunk/twisted/*"):
        if os.path.basename(fname) not in dont_copy_twisted:
            sh('svn cp "%(fname)s" "%(pdir)s/twisted/"' % locals())
            
    package_blacklist = ','.join(twisted_subprojects)
    sh('svn rm "%(pdir)s/bin/"{%(package_blacklist)s}' % locals())
    for fname in glob("../trunk/twisted/topfiles/*"):
        sh('svn cp "%(fname)s" "%(pdir)s/"' % locals())
    sh('svn cp "../trunk/doc/core" "%(pdir)s/doc"' % locals())
    sh('svn cp "../trunk/doc/fun" "%(pdir)s/doc/fun"' % locals())

    sh('svn mkdir "%(pdir)s/admin/sumo/"' % locals())
    sh('svn cp "../trunk/setup.py" "%(pdir)s/admin/sumo/setup.py"' % locals())
    sh('svn cp "../trunk/README" "%(pdir)s/admin/sumo/README"' % locals())

migrate_core()
for proj in twisted_subprojects:
    migrate_subproj(proj)

