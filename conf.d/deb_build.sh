python conf.d/deb_install_build_deps.py $ZBUILDER_NAME/debian/control
cd $ZBUILDER_NAME
debuild -sa -rsudo
