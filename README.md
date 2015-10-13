# zbuilder
Building deb/rpm packages in Docker containers

Here is a small example which builds packages which match `eblob.bedf7bc60806` image substring.
According to `repo.json` config file, it will be only `eblob` package built in `bedf7bc60806` image.

```
sudo python ./zbuilder.py --conf repo.json --image eblob.bedf7bc60806 --build-dir /tmp/docker
```
