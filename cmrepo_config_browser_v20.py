#########################################################
# Author : Cagri Koksal                                 #
# 2019                                                  #
# cmrepo config browser v1.0                            #
# configuration browser for register cmrepo config dump #
#########################################################
import tkinter, tkinter.ttk, sys, paramiko, threading, anytree, time, logging
from tkinter import filedialog, font
from tkinter import *
#########################################################
class configComponent(anytree.Node,):
    scalars={} # dictionary of scalar variables
    table_list={} # array of tables
    table=[] #array of tablerows
    tvindex=""
#########################################################
def searchConfig(top,match):
    #print("calling search....")
    children=tree.get_children(top)
    match=match.lower()
    #print("children",children)
    for child in children:
        if len(tree.item(child)["values"])>0:
            value=tree.item(child)["values"][0].lower()
            ancestor=findTreeViewAncestor(tree,child)
            #print(value, match)
            if value.find(match)>=0:
               tree.item(child,open=True)
               tree.selection_add(child)
               tree.see(child)
               resultlist.insert("end","{0:10} {1:100} {2:200}".format(child,ancestor,tree.item(child)["values"][0]))
               return child
        else:
           searchConfig(child,match)

#########################################################
def pickFile():
    global rootDN
    filename=tkinter.filedialog.askopenfilename(initialdir = "Desktop",title = "Select file",filetypes = (("text files","*.txt"),("all files","*.*")))
    #print(filename)
    fileopenentry.insert("end",filename)
    
    filecontents=readConfigDump(filename)
    cfgtree=configComponent("")
    rootDN.append(cfgtree)

    parseConfig(rootDN[-1],filecontents,tree)
    #print(anytree.RenderTree(rootDN))
#########################################################
def fetchConfig():
    global rootDN
    dn=remoteCommand(hostentry.get(),unameentry.get(),passwordentry.get(),"cmcli lsdn").split("\n")

    for i in range(1,len(dn)):
        if dn[i].find("------")>=0:
            i=i+1
            while dn[i].find("@")<0:
                logging.info("Fetching config for : ",dn[i])
                configdump=remoteCommand(hostentry.get(),unameentry.get(),passwordentry.get(),"cmcli display "+ dn[i].strip())
                timestamp=time.time()
                outputfilename="config_dump_{th}_{tdn}_{ts}.txt".format(th=hostentry.get().split(":")[0],tdn=dn[i].strip(),ts=timestamp)
                print("dumping config to file ",outputfilename)
                writeConfigDump(outputfilename,configdump)
                time.sleep(2)
                filecontents=readConfigDump(outputfilename)
                cfgtree=configComponent(dn[i].strip())
                rootDN.append(cfgtree)
                parseConfig(rootDN[-1],filecontents,tree)
                i=i+1
            break
    
#########################################################   
def getselection(event):
    logging.info(tree.identify_row(event.y),tree.identify_column(event.x))
    logging.info(tree.item(tree.identify_row(event.y))["values"])

def viewselection(event):
    try:
        selection=resultlist.get(resultlist.curselection())
        selection=selection[:selection.find(' ')]
        tree.see(selection)
        tree.selection_add(selection)
    except Excepiton as err:
        logging.info(err)
#########################################################
# returns the anytree node based on given filter
def findConfigTreeParent(rootNode,filter):
    r=anytree.resolver('name')
    r.get(rootNode,"filter")
    if len(result)>1:
        for rootNode in result:
            result=findConfigTreeParent(rootNode,filter)
    elif len(result)==1:
        return result[0]
    else:
        return anytree.Node("none")     
#########################################################
def findTreeViewParent(tree,filter):
    top=''
    for match in filter:
        children=tree.get_children(top)
        for child in children:
            if tree.item(child)["text"]==match:
                top=child
            return top
#########################################################
def findTreeViewAncestor(tree,child):
    parent=tree.parent(child)
    ancestor=""
    while parent!="":
        ancestor=tree.item(parent)["text"]+"/"+ancestor
        parent=tree.parent(parent)
    
    return ancestor
#########################################################
def createNodesFromPath(configTree,treeView,path):
    r=anytree.Resolver('name')
    node_list=path.split('/')
    top=""
    #tvparent="I001"
    tvparent=treeView.get_children()[0]
    for node in node_list:
       try:
        top=top+"/"+node
        if node!=configTree.name:
            #print("checking if in tree ",top)
            configTree=r.get(configTree,top)
            tvparent=configTree.tvindex
       except:
        #print("creating in tree ", node, configTree)
        configTree=configComponent(node,configTree)
        tvparent=treeView.insert(tvparent, "end",text=configTree.name)
        configTree.tvindex=tvparent
        
    return  configTree
#########################################################
def remoteCommand(targetHost,username,password,command):
    port=22
    hostport=targetHost.split(":")
    targetHost=hostport[0]
    result=""
    if (len(hostport) == 2):
        port=hostport[1]
    
    try:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
    
        client.connect(targetHost, port=port, username=username, password=password)

        remote_conn = client.invoke_shell()
        remote_conn.settimeout(5)
        remote_conn.send(command+'\n')
        time.sleep(1)
        #remote_conn.send('cmadmin\n')
        #time.sleep(1)
        #remote_conn.send('yt_xk39b\n')
        result=""
        while True:
            output = remote_conn.recv(65535)
            result=result+str(output,"utf8")
            #print(result)
            if output=="":
                break
            output=""
    except:
        logging.exception("socket.timeout : no more data to read")
    finally:
        client.close()
    return result
#########################################################
def parseConfig(configTree,configDump,tree):
    """    
    Tokens are DNs, COMPONENT, TableName, NumberofRows,=
    """
    #flushConfig()
    
    i=j=k=0
    rootdnset=False
    logging.info("number of lines....",len(configDump))

    for i in range(0,len(configDump)-1):
        line=configDump[i]
        #print("processing line....",i,line)
        if not rootdnset:
            #if "********" in line:
            if "/" in line:
                #line=line[line.find("********")+8:].strip(':')
                rootdn=line[:line.find('/')]
                print("rdn: ",rootdn)
                configTree.name=rootdn
                parent=tree.insert("", 0,text=configTree.name)
                rootdnset=True
                #logging.info("Setting root dn as: ",rootdn)

        #skip empty lines
        if line.strip().strip('\r').strip('\n')=="":
            continue

        #^DN/DU....          
        if line.startswith(configTree.name+"/"):
            line=line.strip(':').strip('')

            currentparent=createNodesFromPath(configTree,tree,line)
            treeparent=currentparent.tvindex
            continue

        if  line.startswith("COMPONENT"):
            component_name=line.split('=')[1].strip(':')
            component=configComponent(component_name,currentparent)
            compparent=tree.insert(treeparent,"end",text=component_name)
            continue
                
        if  line.find("#	Table")>=0:
            table_name=line.split(':')[1].strip()
            component.table_list[table_name]=[]
            i=i+1
            line=configDump[i]
            numrows=int(line.split(':')[1].strip())
            

            if numrows>0:
                tabparent=tree.insert(compparent,"end",text=table_name)
                for j in range(1,numrows+1):
                    i=i+1
                    line=configDump[i]
                    while len(line)>=3:
                        component.table_list[table_name].append(line)
                        tree.insert(tabparent,"end",values=(line.split('=')[0],line.split('=')[1]))
                        i=i+1                     
                        line=configDump[i]
         
        prevline=configDump[i-1]   
        if prevline.startswith("COMPONENT"):
            while len(line)>=3:
                key=line.split('=')[0].strip()
                if len(line.split('='))>1:
                    value=line.split('=')[1].strip()
                else:
                    value=''
                component.scalars[key]=value
                i=i+1
                line=configDump[i]
                tree.insert(compparent,"end",values=(key,value))

#########################################################
def readConfigDump(configfile):
    contents=""
    try:
        file=open(configfile, "r",encoding='utf-8')

        contents=file.read()
        contents=contents.split('\n') 
    except IOError as e:
        logging.exception("Error while reading file :",configfile,e)

    return(contents)
#########################################################
def writeConfigDump(configfile,configdump):
    try:
        print("config dump size",len(configdump))
        configdump=configdump.replace("\r\n", "\n")
        #print("config dump size",len(configdump))

        file=open(configfile, "w",encoding='utf-8')
        file.write(configdump)
        file.close()
    except Exception as e:
        logging.exception("Exception while writing to file: ",configfile,e.errno)
        return False
    return True
#########################################################
def flushConfig():
    global rootDN
    try:
        for item in tree.get_children():
            tree.delete(item)
        resultlist.delete(0,"end")
        for item in rootDN:
            del item
    except:
        pass
#########################################################
def copySelection(event):
    #selection = tree.item(tree.identify_row(event.y))["values"]
    selected_items = tree.selection()
    print(selected_items)
    rootw.clipboard_clear()
    for item in selected_items:
        value =  tree.item(item)['values']
        try:
            rootw.clipboard_append("{0} = {1}".format(value[0],value[1]))
            rootw.clipboard_append('\n')
        except:
            rootw.clipboard_append(tree.item(item)['text'])
            rootw.clipboard_append('\n')       
        else:
            pass

######
def expandAll(tree,child):
    for child in tree.get_children(child):
        tree.item(child,open='TRUE')
        expandAll(tree,child)

def collapseAll(tree,child):
    for child in tree.get_children(child):
        tree.item(child,open='FALSE')
        collapseAll(tree,child)
######
def popupMenu(event):
    popup = tkinter.Menu(rootw,tearoff=0)
    popup.add_command(label="Copy Selection",command=lambda: copySelection(event))
    #popup.add_command(label="Copy Component")
    #popup.add_separator()
    popup.add_command(label="Expand All",command=lambda: expandAll(tree,''))
    popup.add_command(label="Collapse All",command=lambda:collapseAll(tree,''))
    # just to show that event can be passed as an arguement with lamda, otherwise, once right button clicked selectAll called
    popup.tk_popup(event.x_root,event.y_root)

#########################################################

cmrepoIP="10.150.201.153"
sshlogin="root"
sshpass="yt_xk39b"
cmuser="cmadmin"
cmpass="yt_xk39b"
clicommand=""
#########################################################
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='logging.log',
                    filemode='w')
rootDN=[]
result=""
rootw=tkinter.Tk()
myfont=tkinter.font.Font(family="Courier", size=9)
rootw.title("CM Repo Configuration Browser")
optionframe=tkinter.Frame(rootw)
treeframe=tkinter.Frame(rootw)
bottomframe=tkinter.Frame(rootw)
resultframe=tkinter.Frame(rootw)
# style the ttk widget treeview
mystyle=tkinter.ttk.Style()
mystyle.configure('mystyle.Treeview',font=('Courier', 9))
tree=tkinter.ttk.Treeview(treeframe,style='mystyle.Treeview')

tree.bind("<ButtonPress-1>", getselection)
tree.bind("<ButtonPress-3>", popupMenu)

tree["columns"]=("one","two","three")
tree.column("one", width=150 )
tree.column("two", width=150)
tree.heading("one", text="Parameter")
tree.heading("two", text="Value")



Sy = tkinter.Scrollbar(treeframe,orient="vertical",command=tree.yview)
Sx = tkinter.Scrollbar(treeframe,orient="horizontal",command=tree.xview)
Sy.pack(side="right", fill="y")
Sx.pack(side="bottom",fill="x")

hostlabel=tkinter.Label(optionframe,text="Target Host")
unamelabel=tkinter.Label(optionframe,text="CM User name ")
passwordlabel=tkinter.Label(optionframe,text="CM Password ")

hostentry=tkinter.Entry(optionframe)
unameentry=tkinter.Entry(optionframe)
passwordentry=tkinter.Entry(optionframe,show='*')
fetchbutton=tkinter.Button(optionframe,text="Fetch Config",command=fetchConfig)

fileopenlabel=tkinter.Label(optionframe,text="Pick config file ")
fileopenentry=tkinter.Entry(optionframe)

openfilebutton=tkinter.Button(optionframe,text="Browse",command=pickFile)

hostlabel.pack(side="left")
hostentry.pack(side="left")
unamelabel.pack(side="left")
unameentry.pack(side="left")
passwordlabel.pack(side="left")
passwordentry.pack(side="left")
fetchbutton.pack(side="left")

openfilebutton.pack(side="right")
fileopenentry.pack(side="right")
fileopenlabel.pack(side="right")    
                            
searchentry=tkinter.Entry(bottomframe)
searchbutton=tkinter.Button(bottomframe,text="Search parameter ",command=lambda: searchConfig("",searchentry.get()))
searchbutton.pack(side="left")
searchentry.pack(side="left")
flushbutton=tkinter.Button(bottomframe,text="Flush config ",command=lambda: flushConfig())
flushbutton.pack(side="right")


resultlist=tkinter.Listbox(resultframe)
resultlist.config(font=myfont)
LSy = tkinter.Scrollbar(resultframe,orient="vertical",command=resultlist.yview)
LSx = tkinter.Scrollbar(resultframe,orient="horizontal",command=resultlist.xview)
LSy.pack(side="right", fill="y")
LSx.pack(side="bottom",fill="x")
resultlist.bind("<Double-Button-1>", viewselection)
resultlist.pack(fill="both",expand=1)

optionframe.pack(fill="both",expand=0)
treeframe.pack(fill="both",expand=1)
bottomframe.pack(fill="both",expand=0)
resultframe.pack(fill="both",expand=0)

tree.pack(fill="both",expand=1)
rootw.mainloop()
