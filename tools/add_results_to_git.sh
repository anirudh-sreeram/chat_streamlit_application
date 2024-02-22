for i in `ls`
do
	cd $i
	for j in `ls`
	do
		cd $j
		num=`ls -l | wc -l`
		echo $num from $i/$j checked in
		if [ $num -gt 2 ]
		then
			git add .
			git commit -m "Adding $i/$j data into the repo"
			git push
			sleep 5
			echo $num from $i/$j checked in
			sleep 5
		fi
		cd ..
	done
	cd ..
done
