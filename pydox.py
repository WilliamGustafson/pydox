#!/usr/bin/env python
##########################################
##########################################
#TODO:
#the builtin type is a class that is callable
#and the type of any object is of type type.
#Point is, to check if something is a class
#don't do the hacky type(.)==type(str) or whatever
#just do type(.)==type
#
#mess with sizing of entries. Notes on sizing:
#	\huge == \Huge
#	\bf\large is \subsection
#	\bf\Large is \section
#	\bf is \subsubsection
#
#record qualified names of all functions and stuff
#and \verb any occurrences
#
#take a depth option and don't show entries above
#that depth in the table of contents
#
#option to add an index listing all the entries?
#
#Should we execute all blox commands before generating latex?
##########################################
##########################################
r'''
This program generates a LaTeX file from the doc strings of a specified python module.

Usage:
	\begin{addmargin}{2em}\begin{verbatim}
	pydox INPUT_FILE [-p PREAMBLE] [-c]
	\end{verbatim}\end{addmargin}

Example:
\begin{addmargin}{2em}
	Running \verb|pydox pydox.py -c| will produce a tex file \verb|pydox.py.tex| and
	compile it with \verb|pdflatex| producing a pdf \verb|pydox.py.pdf| with documentation
	for this module.
\end{addmargin}

Arguments:
	\begin{enumerate}
		\item[]{\verb|INPUT_FILE| --
			This is the file to produce documentation for.
			The module will be imported and then all attributes will be iterated
			through to extract the doc strings.
			}
		\item[]{\verb|-p --preamble| -- Optionally specify a file whose contents are written
			as the preamble. This should not include \verb|\begin{document}| as after
			the preamble the packages hyperref and scrextend are included and
			an environment 'child' is defined for showing indentation levels.
			}
		\item[]{\verb|-c --compile| -- When this flag is present the generated tex file
			is compiled using pdflatex.
			}
	\end{enumerate}
'''
import sys
import itertools
import importlib
import inspect
import os
import fire
def qualname(o):
	return o.__qualname__ if hasattr(o,'__qualname__') else o.__name__
def baseModule(s):
	if type(s)==type(sys): return baseModule(s.__name__)
	if type(s)!=str: s=s.__module__
	if '.' not in s: return s
	return s[:s.index('.')]

class Dox:
	'''
	A class embodying documentation for a given module.
	'''
	#set up some types
	func_type = type(importlib.import_module)
	module_type = type(importlib)
	class_type = type(str)
	#list of types to document
	doc_types = [func_type, module_type, class_type]
	#dictionary for execcing
	exec_locals={}
	test_results={} #TODO remove testing
	test_locals=exec_locals
	#dictionary of doc'ed objects so we can look up for links
	doc_objs = {}

	def __init__(this, obj, white_modules=None, child_marker=True, parent=None, depth_offset=0):
		r'''
		\verb|obj| is the object to be documented and \verb|white_modules| is a whitelist
		of names of modules to document objects from. Documentation is only generated for
		an object if it is a function, a module or a class and if it is defined in
		a module contained in \verb|white_modules|. The default value of \verb|white_modules|
		is the module containing \verb|obj|.
		'''
		if obj.__name__ in Dox.doc_objs:
			Dox.doc_objs[obj.__name__].append(this)
		else:
			Dox.doc_objs[obj.__name__]=[this]
		this.dox_entries=[]
		this.white_modules = white_modules if white_modules != None else baseModule(obj)

		this.obj = obj
		if type(this.obj) == type(importlib):
			this.type = 'module'
		elif type(this.obj) == type(str):
			this.type = 'class'
		elif type(this.obj) == type(importlib.import_module):
			this.type = 'function'
		else:
			this.type = 'unknown'

		this.section = None
		this.sections_order = tuple()
		this.section_key = ''
		this.sortkey = ''
		this.no_list = False
		this.is_section = False
		this.child_marker = child_marker
		this.children = True
		this.child_filters = []
		this.no_doc = False
		if parent==None:
			this.root = this
			this.parent = this #The celestial being, the source of all thee that birthed itself as no other can, is the Dox object for the module you are generating documentation for
			this.depth = 0
		else:
			this.parent = parent
			this.depth = parent.depth + depth_offset
			this.root = parent.root
#		this.sections = {}
#		this.section_keys = {}
#		data = obj.__doc__.split('@')
#		this.section = DoxEntry.arg(data,'section')
		if this.obj.__doc__==None:
			this.body = ''
		else:
			pre_blox = normalizeInd(this.obj.__doc__).split('@')
			blox=['']
			for pb in pre_blox:
				if len(blox[-1])>0 and blox[-1][-1]=='\\': blox[-1]=blox[-1][:-1]+'@'+pb
				else: blox.append(pb)
			blox = bloxParse(blox, this, 'blox_')
			body = ''.join(blox)
			this.body = body#.replace('#','\#')
			this.body.strip()
			if this.children: this.addDoxEntries(obj)


	def addDoxEntries(this, obj):
		r'''
		Adds all attributes of \verb|obj| to \verb|this| as children to be documented.

		This is called by \verb|__init__| automatically.
		'''
		while hasattr(obj, '__wrapped__'):
#			print(obj.__name__,'is wrapped')
#			input()
			obj = obj.__wrapped__
		for attr in dir(obj):
			value = getattr(obj, attr)
			if attr!='__wrapped__'\
			and type(value) in Dox.doc_types\
			and baseModule(value) in this.white_modules\
			and all(filter(obj, attr) for filter in this.child_filters):
#			and hasattr(value,'__module__')\
				this.dox_entries.append(Dox(value,parent=this,depth_offset=1 if this.is_section else 0))


	def document(this):
		r'''
		Generates a latex document documenting the object provided during construction.
		'''
		#uhh... I guess this is just the beginning and end shell?
		return this.latex()

#	def arg(source,argName,default=None):
#		'''
#		'''
#		if argName not in source:
#			return default
#		return source[source.index(argName)+1]

	def latex(this):
		r'''
		Returns the body text of documentation for the object provided during construction
		and all attributes that are functions, classes or modules.
		'''
		if this.no_doc:
			print('not doccing',this.obj.__name__)
			ret = []
		else:
			header = this.header()
#			#generate header
#			if this.type == 'function':
#				temp = inspect.getsource(this.obj).split('\n')
#				#because of decorators skip lines until there's no @
#				for i in range(len(temp)):
#					if temp[i].strip()[0]!='@': break
#				#because of very long lines we want to break
#				#search for a colon ended line
#				for j in range(i,len(temp)):
#					if temp[j].strip()[-1]==':': break
#				header = [t.strip()[:-1] for t in temp[i:j+1]]
##				header = temp#[:temp.index(':')]
#			elif this.type == 'class':
#				temp = inspect.getsource(this.obj).split('\n')[0]
#				header = [temp[:temp.index(':')]]
#			elif this.type == 'module':
#				header = [this.obj.__name__]
#			header = [h.strip() for h in header]
			######
	#		parent_name = []
	#		parent = this.parent
	#		while(parent!=this.root):
	#			parent_name.append(parent.obj.__name__)
	#			parent = parent.parent
	#		header = '.'.join(parent_name+[header])
			######
			ret = [
#				('\\section{'+
#				'\\texttt{'+
#					(header[0]
#					if len(header)==1
#					else
#					'\\\\\n'+''.join('\\textbf{\\texttt{'+h+'}}\n\\\\' for h in header[1:])
#				)
#				+
#				'}}\n\\label{'+qualname(this.obj)+'}'
#				)
#				if this.is_section
#				else
				#don't list anything for the module itself
				'' if this.parent is this
				else
				'\\textbf{\\hypertarget{'+
				qualname(this.obj)+
				'}{'+
				(('\\'+Dox.depth_to_size(this.depth)+ ' ') if this.is_section else '')+
				'\\texttt{'+
				header[0]+
				'}'+
				'}}'+ (''if len(header)==1 else
					'\\\\\n'+''.join('\\textbf{\\texttt{'+h+'}}\n\\\\' for h in header[1:])
					)
				,
				('' if (this.no_list or this.is_section) else
				(
					'\\addcontentsline{toc}{'
					+ Dox.depth_to_secname(this.depth)
					+ '}{\\protect\\hyperlink{'
					+ qualname(this.obj)#this.obj.__name__
					+ '}{'
	#				+ str(this.depth) #debug
					+ this.obj.__name__.replace('_','\\_')
					+ '}}'
				)),
				r'{\list{}{\leftmargin 0.5cm}\item{'+
				this.insert_links(this.body)
				+r'}\endlist}'
				]
		if len(this.dox_entries)>0 and this.children:
			ret.append('\n')
			if this.child_marker: ret.append('\\begin{child}')
			sections = {} #if this.sections==None else this.sections
#			if sections==None:
#				sections_keys = {}
#			else:
#				section_keys = {S: '' for S in sections}
#				section_keys[None] = ''
#				section_keys.update({} if this.section_keys==None else this.section_keys)

			for de in this.dox_entries:
				if de.is_section:
					if de.obj.__name__ not in sections: sections[de.obj.__name__]=[de]
					else: sections[de.obj.__name__].append(de)
				elif de.section not in sections: sections[de.section]=[de]
				else: sections[de.section].append(de)
			section_keys = {S:(len(this.sections_order), max(de.section_key for de in sections[S])) for S in sections}
			for i in range(len(this.sections_order)):
				S = this.sections_order[i]
				if S in section_keys:
					section_keys[S] = (i,section_keys[S])
				elif S.strip() in section_keys:
					section_keys[S] = (i,section_keys[S])

			for S in sorted(sections.keys(), key=lambda S: section_keys[S]):
				if S!=None:
					sec_type = Dox.depth_to_secname(this.depth+1)
#					sec_type = Dox.depth_to_secname(this.depth)
					ret.append('\\'+sec_type+'{'+
#						str(this.depth+1)+ #debug
						S+'}\n\\label{'+S+'}\n')
#					for de in sections[S]: de.increase_depth()
				sorted_de=[]
				for de in sorted(sections[S],key=lambda x:x.sortkey):
					ret.append(de.latex())
#			for de in this.dox_entries:
#				ret.append(de.latex())
#				ret.append('\n')
			if this.child_marker: ret.append('\\end{child}')
			ret.append('\n')
		ret.append('')
		return '\n'.join(ret)

	def insert_links(this,txt):
		r'''
		Finds all occurrences of \verb|\verbx*x| where x is any character
		and \verb|*| is the name of a documented object and replaces it
		with a link to the documentation.

		If there is only one occurrence of \verb|x| returns the original
		string, the \LaTeX document will have issues.
		'''
		txt_blocks = txt.split('\\verb')
		ret = [txt_blocks[0]]
		for block in txt_blocks[1:]:
			if len(block)==0: continue
			#grab body of verb use as object name
			if block[0] not in block[1:]: return txt
			obj = block[1:][:block[1:].index(block[0])]
			obj_names=obj.split('.')
			if obj_names[-1] not in Dox.doc_objs:
				ret.append('\\verb')
				ret.append(block)
				continue

			#grab all obj's doc'ed with that name
			#and find the one that matches this's qual name best
			names = [qualname(n.obj).split('.') for n in Dox.doc_objs[obj_names[-1]]]
			def filter(n):
				m = min(len(n),len(obj_names))
				return all(n[i]==obj_names[i] for i in range(-1,-m,-1))
			names = [n for n in names if filter(n)]
			this_name = qualname(this.obj).split('.')

			match_lens = []
			for name in names:
				for i in range(min(len(name),len(this_name))):
					if name[i]!=this_name[i]: break
				if i==len(this_name)-1 or i==len(name)-1 and name[i]==this_name[i]: i+=1
				match_lens.append(i)
			if len(match_lens)==0:
				ret.append('\\verb')
				ret.append(block)
				continue
			max_match = max(match_lens)
			#non-unique match no link
			if len([ml for ml in match_lens if ml==max_match])>1:
				#check for unique match in global scope
				match_lens = []
				for name in names:
					for i in range(min(len(name),len(obj_names))):
						if name[i]!=obj_names[i]: break
					if i==len(this_name)-1 or i==len(name)-1 and name[i]==obj_names[i]: i+=1
					match_lens.append(i)
				if len([ml for ml in match_lens if ml==max_match])!=1:
					ret.append('\\verb')
					ret.append(block)
					continue

			#unique match make link
			max_matches = [names[i] for i in range(len(names)) if match_lens[i] == max_match]
			match = [d for d in Dox.doc_objs[max_matches[0][-1]] if qualname(d.obj)=='.'.join(max_matches[0])][0]
			link = r'\hyperlink{{{}}}{{\texttt{{{}}}}}'.format(qualname(match.obj),block[1:][:block[1:].index(block[0])].replace('_','\\_'))

#			ret.append(block[1:][:block[1:].index(block[0])])
			ret.append(link)
			ret.append(block[1:][block[1:].index(block[0])+1:])

#			matches=[]
#			for n in names:
#				if n==this_name:
#					matches.append(n)
#					continue
#				for i in range(min(len(n),len(this_name))):
#					if n[i]!=this_name[i]: break
#				if i==len(n)-1 or i==len(this_name)-1 and n[i]==this_name[i]: i+=1
#				if i>0: matches.append(n[:i])
#			max_matches = max(len(m) for m in matches)
#			max_matches = [m for m in matches if len(m)==max_matches]
#			print('this.insert_links','this =',qualname(this.obj))
#			print('matches',matches)
#			print('max_matches',max_matches)
#			print('verb text',block[1:][:block[1:].index(block[0])])
#			#multiple best matches name is ambiguous
#			if len(max_matches)>1 or len(max_matches)==0:
#				ret.append('\\verb')
#				ret.append(block)
#				continue
#			#unique best match insert link
#			match = [d for d in Dox.doc_objs[max_matches[0][-1]] if qualname(d.obj)=='.'.join(max_matches[0])][0]
#			link = r'\href{{{}}}{{{}}}'.format(match.header(), qualname(match.obj))
#
#			ret.append(block[1:][:block[1:].index(block[0])])
#			ret.append(link)
#			ret.append(block[1:][block[1:].index(block[0])+1:])
		return ''.join(ret)

	def header(this):
		r'''
		Returns a header for a documented object used as a link name and title for documentation.
		'''
		if this.type == 'function':
			temp = inspect.getsource(this.obj).split('\n')
			#because of decorators skip lines until there's no @
			for i in range(len(temp)):
				if temp[i].strip()[0]!='@': break
			#because of very long lines we want to break
			#search for a colon ended line
			for j in range(i,len(temp)):
				if temp[j].strip()[-1]==':': break
			header = [t.strip()[:-1] for t in temp[i:j+1]]
#				header = temp#[:temp.index(':')]
		elif this.type == 'class':
			temp = inspect.getsource(this.obj).split('\n')[0]
			header = [temp[:temp.index(':')]]
		elif this.type == 'module':
			header = [this.obj.__name__]
		return [h.strip().replace('_','\\_') for h in header]

	def increase_depth(this, by=1):
		r'''
		Increase the depth of the documentation entry and all of its children.
		'''
		this.depth += 1
		for de in this.dox_entries:
			de.increase_depth(by)

	def depth_to_size(depth):
		r'''
		Returns the appropriate size for a sectioning level name for the given \verb|depth|, i.e. returns \verb|'huge'|,\verb|'Large'|,\verb|'large'|,\verb|'normalsize'|,\verb|'normalsize'|,$\dots$.
		'''
		sec=Dox.depth_to_secname(depth)
		if sec=='chapter':
			return 'huge'
		if sec=='section':
			return 'Large'
		if sec=='subsection':
			return 'large'
		return 'normalsize'

	def depth_to_secname(depth):
		r'''
		Returns the appropriate sectioning level name for the given \verb|depth|, i.e. returns \verb|'section'|,\verb|'section'|,\verb|'subsection'|,\verb|'subsubsection'|,\verb|'subsubsection'|,$\dots$.
		'''
#		if depth==-1: return 'chapter'
#		if depth==0: return 'section'
#		if depth == 1: return 'subsection'
		if depth==0: return 'part'
		if depth==1: return 'section'
		if depth==2: return 'subsection'
		return 'subsubsection'


#	def Rmarkdown(this):
#		r'''
#		Not implemented.
#		'''
#		raise NotImplementedError()

#this never got implemented and is not worth the trouble
#use something else like pytest or doctest
#	def blox_test(this, blox, current):
#		r'''
#		Implements the \verb|\@test\@\verb| command when parsing doc strings.
#
#		This command lets you embed simple unit tests into doc strings and run
#		them with pydox.
#
#		Usage \verb|\@test\@expected value\@actual value\@|
#
#		For example \verb|\@test\@4\@double(2)\@| will compare \verb|4| against
#		the value of \verb|double(2)|.
#		'''
#		try:
#			test_passed = eval(blox[current],Dox.test_locals) == eval(blox[current+1],Dox.test_locals)
#		except:
#			test_passed = False
#		Dox.test_results[qualname(this.obj)]=test_passed
#		return '',current+2
#	def blox_named_test(this, blox, current):
#		r'''
#		Implements the \verb|\@named_test\@\verb| command when parsing doc strings.
#
#		This command lets you embed simple unit tests into doc strings and run
#		them with pydox.
#
#		Usage \verb|\@named_test\@test name\@expected value\@actual value\@|
#
#		For example \verb|\@named_test\@double test\@4\@double(2)\@| will compare \verb|4| against
#		the value of \verb|double(2)|.
#		'''
#		try:
#			test_passed = eval(blox[current+1],Dox.test_locals) == eval(blox[current+2],Dox.test_locals)
#		except:
#			test_passed = False
#		Dox.test_results[blox[current+1]] = test_passed
#		return '',current+3

	def blox_section(this, blox, current):
		r'''
		Implements the \verb|\@section\@| command when parsing doc stings.

		Usage \verb|\@section\@[SECTION NAME]\@|

		Places the
		documentation entry in a sectioning unit called \verb|[SECTION NAME]|.
		The level of the unit -- section, subsection, subsubsection -- is one
		lower than the parent's (though subsubsection is the lowest). If the
		parent is the top module then the level is section.
		'''
		if current==len(blox): return '',current
		this.section = blox[current]
		this.increase_depth()
#		this.depth = this.parent.depth + 1
#		if this.section not in this.parent.sections: this.parent.sections[this.section] = []
#		this.parent.sections[this.section].append(this)
#		if this.section_key!=None:
#			this.parent.section_keys[this.section] = this.section_key
		return '',current+1
	def blox_section_key(this, blox, current):
		r'''
		Implements the \verb|\@section_key\@| command when parsing doc strings.

		Usage \verb|\@section_key\@KEY\@|

		Sets the documentation entry's section's section key to \verb|KEY|. The
		sections are sorted by their keys, the default key is \verb|''|. The keys
		are sorted as string. This
		should only be set in one doc string per section, or \verb|\@sections_order\@|
		should be used instead. If this command is used in multiple documentation
		entries with the same section the key will be whichever is parsed last
		which is determined by \verb|Python|'s ordering when iterating through
		the module's attributes.
		'''
		if current==len(blox): return '',current
		this.section_key = blox[current]
#		if this.section!=None:
#			this.root.section_keys[this.section] = blox[current]
#		else:
#			this.section_key = blox[current]
		return '',current+1
	def blox_sections_order(this, blox, current):
		r'''
		Implements the \verb|\@sections_order\@| command when parsing doc strings.

		Usage \verb|\@sections_order\@S_1\@...\@S_n\@|

		Orders the sections containing immediate children as \verb|S_1|
		through \verb|S_n| (The \verb|S_i| are section names).
		'''
		if current==len(blox): return '',current
		this.sections_order = []
		while blox[current]!='' and current<len(blox):
			this.sections_order.append(blox[current])
			current+=1
		return '',current+1
	def blox_sortkey(this, blox, current):
		r'''
		Implements the \verb|\@sortkey\@| command when parsing doc strings.

		Usage \verb|\@sortkey\@KEY\@|

		Within a section documentation entries are ordered via their
		sort keys, which default to \verb|''|. The keys are sorted as strings.
		'''
		if current==len(blox): return '',current
		this.sortkey = blox[current]
		return '',current

	def blox_eval(this, blox, current):
		r'''
		Implements the \verb|\@eval\@| command when parsing doc strings.

		Usage \verb|\@eval\@CODE\@|

		The string \verb|CODE| is evaluated via \verb|eval| and these two blocks
		are replaced with the result. All eval and exec blocks share the same
		locals dictionary.
		'''
		if current==len(blox): return '',current
		return str(eval(blox[current], Dox.exec_locals)), current+1

	def blox_exec(this, blox, current):
		r'''
		Implements the \verb|\@exec\@| command when parsing doc strings.

		Usage \verb|\@exec\@CODE\@|

		The string \verb|CODE| is executed via \verb|exec|. There is no output
		for these two blocks. All exec and eval blocks share the same locals
		dictionary.
		'''
		if current==len(blox): return '', current
		exec(blox[current], Dox.exec_locals)
		return '', current+1

	def blox_no_list(this, blox, current):
		r'''
		Implements the \verb|\@no_list\@| command when parsing doc strings.

		Usage \verb|\@no_list\@|

		This documentation entry will not be listed in the table of contents.
		'''
		this.no_list = True
		return '', current

	def blox_no_doc(this, blox, current):
		r'''
		Implements the \verb|\@no_doc\@| command when parsing doc strings.

		Usage \verb|\@no_doc\@|

		This documentation entry will not appear.
		'''
		this.no_doc = True
		return '', current
	def blox_is_section(this, blox, current):
		r'''
		Implements the \verb|\@is_section\@| command when parsing doc strings.

		Usage \verb|\@is_section\@|

		This documentation entry is listed in the table of contents as a section.
		'''
		this.is_section = True
#		this.depth = this.parent.depth + 1
		return '', current

	def blox_no_children(this, blox, current):
		r'''
		Implements the \verb|\@no_children\@| command when parsing doc strings.

		Usage \verb|\@no_children\@|

		No attributes of the documented object will be documented. For example, when
		placed on a class the class is documented but none of its methods are.
		'''
		this.children = False
		return '', current

	def blox_subclass(this, blox, current):
		r'''
		Implements the \verb|\@subclass\@| command when parsing doc strings.

		Usage \verb|\@subclass\@|

		Flags the object as a subclass. Only attributes of the subclass that
		are not attributes of a superclass are documented.
		'''
		this.child_filters.append(lambda obj, attr: all(attr=='__init__' or attr not in dir(base) for base in obj.__bases__))
		return '',current

def normalizeInd(s):
	r'''
	Given a string normalizes the indentation.

	The first nonwhitespace line is found and the number of leading tabs or
	spaces is assumed to be the indentation level. If all nonwhitespace lines
	start with that indentation then it is removed. Otherwise the same
	string is returned.
	'''
	#grab first nonempty line
	lines = s.split('\n')+[None]
	for line in lines:
		if len(line)>0 and not line.isspace(): break
	if line==None: return s
	ws = line[0]
	if ws not in [' ','\t']: return s
	for i in range(len(line)):
		if line[i]!=ws: break
	if any(l!='' and (not l.isspace() and not l.startswith(i*ws)) for l in lines[:-1]): return s
	return '\n'.join(l[i:] for l in lines[:-1])

def bloxParse(blox, commands, func_prefix=''):
	r'''
	Given a list of text blocks interpret and execute it as a blox program using the
	given list of commands.

	Commands can be either a dictionary or a custom object. When commands is a dictionary
	the keys represent command names the blocks can use to call functions, which are
	the values. When commands is a custom object a dictionary is used whose keys are the
	names of function attributes of the object that start with \verb|func_prefix| and values are the
	functions.

	The functions provided should take two parameters: the blocks list and an index to the
	current block. The functions should return two parameters: a string representing output
	of the command to be written in place of the current block and an index to the new
	current block. Note any skipped blocks (i.e. if a commmand returns a higher current block index)
	are not written.
	'''
	if type(commands)!=dict:
		commands = {a[len(func_prefix):] : getattr(commands,a) for a in dir(commands) if callable(getattr(commands,a)) and a.startswith(func_prefix)}
	current = 0 #index into blox
	output = []
	while current < len(blox):
		if blox[current] not in commands:
			block_output = blox[current]
			next = current+1
		else:
			block_output, next = commands[blox[current]](blox, current+1)
		current = next
		output.append(block_output)
	return output

def fullargspec_str(spec):
	r'''
	Given an arg spec returns a string for documenting the function.
	'''
	ret = []
	if spec.defaults == None:
		defaults = [None]*len(spec.args)
	else:
		defaults = [d for d in spec.defaults] + [None]*(len(spec.args)-len(spec.defaults))
	for i in range(len(spec.args)):
		if defaults[i]!=None:
			ret.append(spec.args[i]+'='+repr(defaults[i]))
	return ','.join(ret)
	#TODO varargs, varkwargs, kwonlyargs,kwonlydefaults,annotations


def main(module='',title='',author='',date=False, imp=tuple(),impall=tuple(),whitelist=tuple(),outdir='.',preamble='',packages=tuple(),post='',compile=False):

	exec_import = imp if isinstance(imp,tuple) else (imp,)
	if exec_import:
		exec('import sys', Dox.exec_locals)
		for ei in exec_import:
			ei = os.path.realpath(ei)
			ei_file = os.path.basename(ei)
			ei = ei[:-len(ei_file)]
			if ei_file[-3:]=='.py': ei_file = ei_file[:-3]
			exec('sys.path.append("'+os.path.realpath(ei)+'")', Dox.exec_locals)
			exec('import '+ei_file,Dox.exec_locals)

	exec_import_all = impall if isinstance(impall,tuple) else (impall,)
	if exec_import_all:
		exec('import sys', Dox.exec_locals)
		for ei in exec_import_all:
			ei = os.path.realpath(ei)
			ei_file = os.path.basename(ei)
			ei = ei[:-len(ei_file)]
			if ei_file[-3:]=='.py': ei_file = ei_file[:-3]
			exec('sys.path.append("'+os.path.realpath(ei)+'")', Dox.exec_locals)
			exec('from '+ei_file+' import *', Dox.exec_locals)

	#import the module to document
	module_path = os.path.realpath(module)
	module_name = os.path.basename(module_path)
	if module_name[-3:] == '.py': module_name = module_name[:-3]
	sys.path.append(module_path[:-len(module_name)])
	try:
		module = importlib.import_module(module_name)
	except Exception as e:
		print(f'Unable to import module {module}. Exception: {e}')
	globals()[module.__name__] = module
	#files to doc
	white_modules = whitelist if isinstance(whitelist,tuple) else (whitelist,)
	modules = (module.__name__,) + white_modules
	dox = Dox(module,modules,child_marker=False)

	outdir = os.path.realpath(outdir)

	with open(os.path.join(outdir,module_name+'.tex'),'w') as file:
		if preamble:
			with open(preamble,'r') as file2:
				preamble=file2.read()
		else:
			preamble='\\documentclass[12pt]{article}\n\\usepackage[margin=0.5in]{geometry}\n'
		file.write(preamble)
		#TODO move these into the Dox class and provide preamble as an arg to document(0
		file.write('\\usepackage{hyperref,scrextend}\n\\setlength{\\parindent}{0em}\n') #TODO check for \setlength{\parindent}
		file.write('\\newcommand{\\indentation}{2em}\n')
		file.write(r'''\usepackage{mdframed}
\mdfdefinestyle{childframe}{%
	leftmargin=1em,%
	innerleftmargin=1em,%
	rightmargin=0,%
	innerrightmargin=0,%
	innertopmargin=0%,
	innerbottommargin=0%
	}

\newmdenv[%
  topline=false,%
  bottomline=false,%
  rightline=false,%
  skipabove=\topsep,%
  skipbelow=\topsep,%
  style=childframe,%
]{child}
''')
		file.write('\\setcounter{secnumdepth}{0}\n')
		pkgs = packages if isinstance(packages,tuple) else (packages,)
		if os.path.isfile(os.path.join(outdir,module_name)+'.sty'):
#			 pkgs = module_name+',' + ('' if pkgs == None else pkgs)
			 pkgs = ','.join(itertools.chain((module_name,),((pkgs,) if pkgs else tuple())))
		if pkgs:
			file.write('\\usepackage{'+'}\n\\usepackage{'.join(pkgs.split(','))+'}\n')
		file.write('\\begin{document}\n')
		if title: file.write(f'\\title{{{title}}}\n')
		if author: file.write(f'\\author{{{author}}}\n')
		if date=='today': file.write('\\date{\\today}\n')
		elif date: file.write(f'\\date{{{date}}}\n')
		if any((title,author,date)):
			file.write(f'\\maketitle\n')
		file.write('\\tableofcontents\n')
		file.write('\\setlength{\\parskip}{\\baselineskip}\n') #TODO check for \\setlength{\\parskip}
		file.write(dox.document())
		if post:
			with open(post,'r') as post_file:
				file.write(post_file.read())
				file.write('\n')
		file.write('\\end{document}')

	if compile=='bibtex':
		os.system('pdflatex '+module_name+' && bibtex '+module_name+2*(' && pdflatex '+module_name))
	elif compile:
		os.system('pdflatex '+module_name+ ' && pdflatex '+module_name)

if __name__=="__main__":
	fire.Fire(main)
