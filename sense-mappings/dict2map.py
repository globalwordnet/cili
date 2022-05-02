import sys,os,re

""" when called on a WordNet data.* file, extrapolate sense IDs and concept ID 
	note that we do not produce the sense key, but a sense prefix, optionally, this can be followed, either by ":" (i.e., ending in "::") or ":"-separated addenda
	(for which it is not clear where they come from)

"""

pos2nr_sfx={
	"n": ("1","n"),
	"v": ("2","v"),
	"adj": ("3","a"),
	"a": ("3","a"),
	"adv": ("4","r"),
	"r": ("4","r"),
	"s": ("5","s")

}

for file in sys.argv[1:]:
	with open(file,"rt", errors="ignore") as input:
		for line in input:
			if line[0] in "0123456789":
				line=line.strip()
				fields=line.split()
				synset=fields[0]
				field=fields[1]
				pos=fields[2]
				if not pos in pos2nr_sfx:
					sys.stderr.write("unsupported pos \""+pos+"\" in \""+line+"\"\n")
					sys.stderr.flush()
				else:
					# if pos=="s":
					# 	print("# "+line)
					posnr,pos=pos2nr_sfx[pos]
					synset=synset+"-"+pos
					# lemmas=int(fields[3]) #??? can be 0d in WN31
					fields=fields[4:]
					while not fields[0][0] in "0123456789":
						lemma=fields[0]
						nr=fields[1]
						if len(nr)==1:
							nr="0"+nr 
						sense=lemma+"%"+posnr+":"+field+":"+nr+":"
						if pos!="s":
							sense=sense+":"
							# s phrases have disambiguating suffixes
						print(synset+"\t"+sense)
						fields=fields[2:]



