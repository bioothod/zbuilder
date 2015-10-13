#!/usr/bin/python

import argparse
import docker
import json
import logging
import os
import shutil
import sys

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)


class zbuilder():
    def __init__(self, config):
        js = json.load(config)

        self.docker_files = []
        self.build_succeeded_file = "/tmp/build_succeeded"

        packages = js.get("packages")
        if not packages:
            logging.error("core: there is no 'packages' object, nothing to build")
            return

        logging.info("Starting parse different build types")

        for package_type, package in packages.items():
            images = []
            if package_type == "deb":
                img = js.get("deb-images")
                if img:
                    images += img
            elif package_type == "rpm":
                img = js.get("rpm-images")
                if img:
                    images += img
            else:
                logging.error("%s: unsupported package type", package_type)
                continue

            logging.info("%s: starting to parse commands", package_type)

            pre_build_commands = package.get("pre-build-commands")
            build_commands = package.get("build-commands")
            if build_commands:
                build_commands.append("echo success > %s" % (self.build_succeeded_file))

            post_build = package.get("post-build-commands")
            final_commands = {}
            if post_build:
                pbs = post_build.get("success")
                if pbs:
                    final_commands["success"] = pbs
                pbf = post_build.get("fail")
                if pbf:
                    final_commands["fail"] = pbf
                pba = post_build.get("always")
                if pba:
                    final_commands["always"] = pba

            sources = package.get("sources")
            if not sources:
                logging.error("%s: there is no 'sources' object, nothing to build", package_type)
                break

            for name, source in sources.items():
                logging.info("%s/%s: starting to parse source", package_type, name)

                include_images = source.get("include-images")
                if include_images:
                    images += include_images
                exclude_images = source.get("exclude-images")
                if exclude_images:
                    tmp = []
                    for x in images:
                        if x in exclude_images:
                            continue
                        tmp.append(x)

                    images = tmp

                logging.info("%s/%s: images: %s", package_type, name, ', '.join(images))

                fetch_commands = []
                try:
                    stype = source["type"]
                    repo = source["repository"]
                    branch = source.get("branch", "master")

                    if stype == "git":
                        fetch_commands.append("rm -rf %s" % (name))
                        fetch_commands.append("git clone %s %s" % (repo, name))
                        fetch_commands.append("cd %s" % (name))
                        fetch_commands.append("git checkout %s" % (branch))
                        build_commands.append("cd %s" % (name))
                    else:
                        logging.error("%s/%s: unsupported source type '%s'", package_type, name, stype)
                        continue
                except Exception as e:
                    logging.error("%s/%s: invalid source: %s", package_type, name, e)
                    continue

                logging.info("%s/%s: fetch commands: %s", package_type, name, ', '.join(fetch_commands))
                commands = []
                try:
                    commands.append(pre_build_commands)
                    commands.append(fetch_commands)
                    commands.append(build_commands)
                except Exception as e:
                    logging.notice("%s/%s: could not append command: %s", package_type, name, e)

                for image in images:
                    df = self.generate_dockerfile(name, image, commands, final_commands)
                    self.docker_files.append(df)

    def generate_dockerfile(self, name, image, commands, final_commands):
        df = "Dockerfile.%s.%s" % (name, image)
        with open(df, 'w+') as f:
            f.write("FROM %s\n" % (image))
            f.write("ENV ZBUILDER_IMAGE=%s ZBUILDER_NAME=%s DEBIAN_FRONTEND=noninteractive\n" % (image, name))
            f.write("ADD conf.d conf.d\n")

            for cmd_set in commands:
                cs = "RUN %s\n" % (' && \\\n'.join(cmd_set))
                f.write(cs)

            success = final_commands.get("success")
            if success:
                cs = "RUN test -f %s && \\\n %s\n" % (self.build_succeeded_file, ' && \\\n'.join(success))
                f.write(cs)

            fail = final_commands.get("fail")
            if fail:
                cs = "RUN test -f %s || \\\n %s\n" % (self.build_succeeded_file, ' && \\\n'.join(fail))
                f.write(cs)

            always = final_commands.get("always")
            if always:
                cs = "RUN %s\n" % ' && \\\n'.join(always)
                f.write(cs)

        return df

    def run(self, name = None, build_dir = '.'):
        c = docker.Client(base_url='unix://var/run/docker.sock')

        for path in self.docker_files:
            if name and not name in path:
                continue

            try:
                shutil.rmtree(path="%s/" % build_dir, ignore_errors=True)
                os.mkdir("%s/" % build_dir)
                shutil.copy(path, "%s/" % build_dir)
                shutil.copytree("conf.d", "%s/conf.d" % build_dir)
            except Exception as e:
                logging.error("Could not copy local content to destination build dir %s: %s",
                        build_dir, e)
                continue

            with open("%s.build.log" % (path), "w+") as out:
                response = c.build(path=build_dir, dockerfile=path, rm=False, pull=False, forcerm=False)
                for r in response:
                    out.write(r)
                    logging.info("%s: %s", path, r)

if __name__ == '__main__':
    bparser = argparse.ArgumentParser(description='Builder arguments.', add_help=True)
    bparser.add_argument("--conf", dest='conf', action='store', type=argparse.FileType('r'),
            required=True, help='Input config file.')
    bparser.add_argument("--build-dir", dest='build_dir', action='store', default=".",
            help='Local directory where build process will run.')
    bparser.add_argument("--image", dest='image', action='store',
            help='Build only images containing this substring.')

    args = bparser.parse_args()

    try:
        zb = zbuilder(config=args.conf)
        try:
            zb.run(name=args.image, build_dir=args.build_dir)
        except Exception as e:
            logging.error("Could not run build, name: %s: %s", args.image, e)
    except Exception as e:
        logging.error("Could not create zbuilder object: %s", e)
