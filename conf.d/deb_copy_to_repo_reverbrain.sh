name=`echo $ZBUILDER_IMAGE | awk -F ":" {'print $2'}`
ssh ioremap.net mkdir $name
scp *.deb ioremap.net:/tmp/$name/
