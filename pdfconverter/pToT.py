from cStringIO import StringIO
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
import os
import os.path
import sys, getopt
from pprint import pprint
import re

MIN_RANGE_SIZE = 100

errors = []
emptyTxt = []

endMarks = [".", "?", "!"]
hasNoAbstract = []
hasNoReference = []
hasNoRange = []
inASCII = []
MAX_LENGTH = 196
#converts pdf, returns its text content as a string
#from https://www.binpress.com/tutorial/manipulating-pdfs-with-python/167
def convert(fname, pages=None):
    try:
        if not pages:
            pagenums = set()
        else:
            pagenums = set(pages)

        output = StringIO()
        manager = PDFResourceManager()
        converter = TextConverter(manager, output, laparams=LAParams())
        interpreter = PDFPageInterpreter(manager, converter)

        infile = file(fname, 'rb')
        for page in PDFPage.get_pages(infile, pagenums):
            interpreter.process_page(page)
        infile.close()
        converter.close()
        text = output.getvalue()
        output.close
        return text
    except Exception as err:
        errors.append((fname, err))
        return None

#converts all pdfs in directory pdfDir, saves all resulting txt files to txtdir
def convertMultiple(pdfDir, txtDir):
    if pdfDir == "": pdfDir = os.getcwd() + "\\" #if no pdfDir passed in
    for pdf in os.listdir(pdfDir): #iterate through pdfs in pdf directory
        fileExtension = pdf.split(".")[-1]
        if fileExtension == "pdf":
            pdfFilename = pdfDir + '/' + pdf
            textFilename = txtDir + '/' + pdf + ".txt"
            if not os.path.isfile(textFilename):
                text = convert(pdfFilename) #get string of text content of pdf
                if not text is None:
                    textFile = open(textFilename, "w") #make text file
                    textFile.write(text) #write text to text file

def findRange(content):
    start = 0
    end = len(content)
    for index, line in enumerate(content):
        if "ABSTRACT" in line.replace(' ','').upper() or "PURPOSE" in line.replace(' ', '').upper() or "INTRODUCTION" in line.replace(' ', '').upper():
            start = index
            break
    for index, line in enumerate(content):
        if ("ACKNOWLEDGMENTS" in line.replace(' ', '').upper() or "REFERENCES" in line.replace(' ', '').upper()) and index > start:
            end = index
    return start, end

def isASCII(content):
    return content[0][:5] == '(cid:'

def convertASCII(content):
    converted = []
    # print(content)
    for line in content:
        converted_l = ''
        for c in re.compile('(cid:[0-9]+)').split(line):
            if c[:3] == 'cid':
                converted_l += chr(int(c[4:]))
            elif c == ') (':
                converted_l += ' '
            # elif c == '\n':
            #     converted_l += '\n'
            # if c[:3] == 'cid':
            #     converted_l += str(chr(int(c[4:])))
            # elif c == ' ':# or c == '\n':
            #     converted_l += str(c)
        converted_l += '\n'
        converted.append(converted_l)
    return converted

def convertContent(content, start, end):
    converted = []
    sentence = ""
    for i in range(start, end):
        line = content[i]
        if len(line) > 0 and line[len(line)-1] == '.':
            line += ' '

        parts = [p+'.' for p in line.split('. ') if p]
        if len(parts) > 0 and line[len(line)-2:len(line)-1] != '. ':
            parts[len(parts)-1] = parts[len(parts)-1][:len(parts[len(parts)-1])-1]

        for part in parts:
            if len(sentence) == 0: # start new sentence
                sentence = part
            else:
                sentence += part
                if part[len(part)-1] == '.':
                    if len(sentence.split(' ')) < MAX_LENGTH:
                        converted.append(sentence)
                        sentence = ""
        if len(sentence) > 0:
            # sentence is not finished at the end of the line
            sentence += ' '
    return converted

def formatText(filename):
    try:
        formattedText = ""
        f = open(filename)
        content = f.readlines()

        if len(content) == 0:
            emptyTxt.append(filename)
            return None

        if isASCII(content):
            inASCII.append(filename)
            content = convertASCII(content)

        content = filter(lambda a: a != '\n', content) # remove blank lines
        content = [line[:len(line)-1] for line in content]


        sentence = ""
        start, end = findRange(content)
        if start == 0:
            hasNoAbstract.append(filename)
        if end == len(content):
            hasNoReference.append(filename)
        if end-start+1 > MIN_RANGE_SIZE:
            # print((start, end, content[start], content[end]))
            content = convertContent(content, start, end)
            formattedText = '\n'.join(content)
            # print(filename)
        else:
            hasNoRange.append((filename, start, end))
            return None
        # if (start == 3459):
        #     print(filename)
        #     print((start, end, content[start], content[end-1]))

        # for line in content:
        #     for part in line.split(". "):
        #         print(part)
        #     print("=======")
            # if sentence == "": # start new sentence
            #
            # if "ABSTRACT" in line:
            #     hasAbstract.append(filename)
            #     break

        return formattedText
    except Exception as err:
        errors.append((filename, err))
        # print(filename)
        raise err
        return None

def formatMultiple(txtDir, formattedDir):
    global MAX_LENGTH
    # i = 0
    if txtDir == "": txtDir = os.getcwd() + "\\" #if no txtDir passed in
    for file in os.listdir(txtDir): #iterate through text files in txt directory
        fileExtension = file.split(".")[-1]
        if fileExtension == "txt":
            filename = txtDir + '/' + file
            formatname = formattedDir + '/' + file + '.txt'
            if not os.path.isfile(formatname):
                text = formatText(filename) #get string of text content of file
                if not text is None:
                    textFile = open(formatname, "w") #make text file
                    textFile.write(text) #write text to text file
        # i+=1
        # if i == 3:
        #     break


#i : info
#p : pdfDir
#t = txtDir
def main(argv):
    pdfDir = ""
    txtDir = ""
    formattedDir = ""
    try:
        opts, args = getopt.getopt(argv,"ip:t:f:")
    except getopt.GetoptError:
        print("pdfToT.py -p <pdfdirectory> -t <textdirectory> -f <formatteddirectory>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-i":
            print("pdfToT.py -p <pdfdirectory> -t <textdirectory> -f <formatteddirectory>")
            sys.exit()
        elif opt == "-p":
            pdfDir = arg
        elif opt == "-t":
            txtDir = arg
        elif opt == "-f":
            formattedDir = arg
    convertMultiple(pdfDir, txtDir)
    print('Convert to PDF - Errors for : ')
    pprint(errors)
    formatMultiple(txtDir, formattedDir)
    print("=====")
    print('Empty Texts are :')
    pprint(emptyTxt)
    print("=====")
    print("Files without abstract :")
    pprint(hasNoAbstract)
    print("=====")
    print("Files without reference :")
    pprint(hasNoReference)
    print("=====")
    print("Files without range :")
    pprint(hasNoRange)
    print("=====")
    print("Files in ASCII :")
    pprint(inASCII)
    print("Longest sentence : " + str(MAX_LENGTH))


if __name__ == "__main__":
    main(sys.argv[1:])
