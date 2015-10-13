#!/usr/bin/python

import apt
import apt.progress
import apt_pkg
import logging
import re
import sys

logging.basicConfig(filename1='/var/log/supervisor/rps.log',
        format='%(asctime)s %(levelname)s: deb_install: %(message)s',
        level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)

class control_parser():
    def __init__(self):
        apt_pkg.init()
        self.cache = apt.Cache()
        self.cache.update()
        self.cache.open()

    def parse(self, path = 'debian/control'):
        try:
            tagfile = apt_pkg.TagFile(path)
            for section in tagfile:
                deps = section.get('Build-Depends', None)
                if not deps:
                    continue

                packages = deps.split(',')
                for p in packages:
                    self.mark_install(p)

                self.install()
        except Exception as e:
            print "E: %s" % e

    def mark_install(self, pstr):
        deps = apt_pkg.parse_depends(pstr)
        have_version = False
        for ord in deps:
            if have_version:
                break

            print pstr, ord
            for d in ord:
                name = d[0]
                version_num = d[1]
                version_op = d[2]

                p = self.cache[name]
                if not p:
                    logging.error("Could not find package %s in cache", name)
                    continue

                if len(version_num) > 0:
                    highest_v = None
                    highest_vnum = 0

                    for version in p.versions:
                        if apt_pkg.check_dep(version.version, version_op, version_num):
                            have_version = True
                            logging.info("package: %s, version: %s, priority: %s/%d",
                                    name, version.version, version.priority, version.policy_priority)

                            if (version.policy_priority > highest_vnum):
                                highest_vnum = version.policy_priority
                                highest_v = version

                    if not have_version:
                        logging.error("Could not required version of the package %s, must be %s %s",
                                name, version_op, version_num)
                        # going for the next ORed version if any
                        continue

                    p.candidate = highest_v
                    logging.info("package %s, selected version: %s, priority: %s/%d",
                            name, p.candidate.version, p.candidate.priority, p.candidate.policy_priority)

                logging.info("Going to install package %s", name)
                p.mark_install(auto_fix=True, auto_inst=True)
                have_version = True

                # do not run for the subsequent ORed packages
                break

        if not have_version:
            logging.fatal("Could not find suitable package %s", pstr)

    def install(self):
        self.cache.commit()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "E: usage: %s /path/to/debian/control" % sys.argv[0]

    cp = control_parser()
    cp.parse(path = sys.argv[1])
