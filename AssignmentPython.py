#!/usr/bin/env python
# coding: utf-8

import re
from io import StringIO
from html.parser import HTMLParser
from nltk.tokenize import word_tokenize
import string
from unidecode import unidecode
from urllib.parse import urlparse

#read warc file
def readWARC(filename):
    f = open(filename)
    htmlDict = dict()
    responselist = []
    htmllist = []
    response = ""
    temp = ""
    boolRestart  = False
    boolResponse = False
    boolContent = False
    boolDoctype = False
    for line in f:
        if 'WARC/1.0' in line:
            boolRestart  = True
            boolContent = False
            boolDoctype = False
            if len(temp)>0:
                responselist.append(response)
                htmllist.append(temp)
                htmlDict[response]=temp
            temp=""
            response = ""
        if 'WARC-Type: response' in line:
            boolResponse = True
        if boolResponse == True and boolRestart == True:
            if 'WARC-Target-URI:' in line:
                response = line.lstrip('WARC-Target-URI:').strip()
                boolRestart = False
                boolResponse = False
        if 'Content-Type: text/html' in line:
            boolContent = True
            temp =""
        if boolContent == True:
            if '<!DOCTYPE html>' in line:
                boolDoctype = True
            if boolDoctype == True:
                temp+=line.strip()
    return htmlDict,responselist,htmllist

#strip down html tags
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()
    def handle_data(self, d):
        self.text.write(d+" ")
    def get_data(self):
        return self.text.getvalue()

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

# removes a list of words (ie. stopwords) from a tokenized list.
def removeWords(listOfTokens, listOfWords):
    return [token for token in listOfTokens if token not in listOfWords]

# remove punctations
def removePunctuations(listOfTokens):
    test_joined=' '.join(listOfTokens)
    punc = string.punctuation
    punc = punc.replace('.','')
    test_punc_removed = [char for char in test_joined if char not in punc]
    test_punc_removed_join = ''.join(test_punc_removed)
    return [word for word in test_punc_removed_join.split()]

# removes any words composed of less than 2
def twoLetters(listOfTokens):
    twoLetterWord = []
    for token in listOfTokens:
        if len(token) < 2 :
            twoLetterWord.append(token)
    return twoLetterWord

#format HTML
def formatHTML(htmllist):
    pattern1 = r"(?is)(<script[^>]*>)(.*?)(</script>)"
    pattern2 = r"(?is)(<style[^>]*>)(.*?)(</style>)"
    pattern3 = r"(?is)(<title[^>]*>)(.*?)(</title>)"
    for i in range(len(htmllist)):

        #remove script tags
        htmllist[i] = re.sub(pattern1,'',htmllist[i])
        #remove style tags
        htmllist[i] = re.sub(pattern2,'',htmllist[i])
        #remove title tag
        htmllist[i] = re.sub(pattern3,'',htmllist[i])
        #strip out html tags
        htmllist[i]=strip_tags(htmllist[i])

        #remove special characters and leave only words
        htmllist[i]=re.sub('\W_',' ', htmllist[i])

        # removes numbers and words concatenated with numbers IE h4ck3r. Removes road names such as BR-381.
        htmllist[i]=re.sub("\S*\d\S*"," ", htmllist[i])

        htmllist[i] = htmllist[i].replace(u'\ufffd', '8')    # Replaces the ASCII '�' symbol with '8'
        htmllist[i] = htmllist[i].replace(',', '.')          # Replace commas with period for split
        htmllist[i] = htmllist[i].replace('?', '.')          # Replace question marks with periods for split
        htmllist[i] = htmllist[i].rstrip('\n')               # Removes line breaks
        htmllist[i] = htmllist[i].casefold()                 # Makes all letters lowercase
        #htmllist[i] = htmllist[i].replace(u'\xa0', u'')     # Replaces \xa0 with ''

        listOfTokens = word_tokenize(htmllist[i])
        twoLetterWord = twoLetters(listOfTokens)
        listOfTokens = removeWords(listOfTokens, twoLetterWord)

        listOfTokens = removePunctuations(listOfTokens)

        htmllist[i]   = " ".join(listOfTokens)
        htmllist[i] = unidecode(htmllist[i])
    return htmllist

#create a cleaned dict
def cleanedDictCreator(htmllist, responselist):
    domainDict = dict()
    domainOnly =[]
    for i in range(len(responselist)):
        domain = urlparse(responselist[i]).netloc
        domainOnly.append(domain)
        domainDict[responselist[i]] = htmllist[i]
    return domainDict

#create dictonaries countrywise
def countryDict(domainDict):
    auDict = dict()
    caDict =dict()
    ukDict = dict()
    auDomain =[]
    caDomain =[]
    ukDomain =[]
    for k, v in domainDict.items():
        temp = urlparse(k).netloc
        if temp[len(temp)-3:]=='.au':
            auDict[k]=v
            auDomain.append(k)
        elif temp[len(temp)-3:]=='.ca':
            caDict[k]=v
            caDomain.append(k)
        elif temp[len(temp)-3:]=='.uk':
            ukDict[k]=v
            ukDomain.append(k)
    return auDict, caDict,ukDict

#positive and negative list creation
def posNegListCreator(posText,negText):
    positiveWords = [line.rstrip('\n') for line in open(posText)]
    negativeWords =[line.rstrip('\n') for line in open(negText)]
    return positiveWords,negativeWords

#find positive words in .au domains
def auGenPosNeg(auDict,positiveWords,negativeWords):
    pnDict = dict()
    for k,v in auDict.items():
        negativePage = 0
        positivePage = 0
        rawPositive=0
        rawNegative=0
        ratio = 0
        pnArray =[]
        lineList =auDict[k].split('.')
        for i in range(len(lineList)):
            wordList = lineList[i].split(' ')
            positiveCount=0
            negativeCount=0
            for j in range(len(wordList)):
                if wordList[j].strip() in positiveWords:
                    positiveCount+=1
                    rawPositive+=1
                if wordList[j].strip() in negativeWords:
                    negativeCount+=1
                    rawNegative+=1
            if negativeCount == 2:
                positivePage+=1
            elif positiveCount>0 and negativeCount==0:
                positivePage+=1
            elif negativeCount>0 and positiveCount==0:
                negativePage+=1
            elif negativeCount>positiveCount:
                negativePage+=1
            elif positiveCount>negativeCount:
                positivePage+=1
            elif positiveCount==negativeCount and positiveCount!=0:
                positivePage+=1 
        if rawNegative!=0:
            ratio = float(rawPositive)/rawNegative
        pnArray =[rawPositive,rawNegative,ratio,positivePage,negativePage]
        pnDict[k]=pnArray
    
    posTot=0
    negTot=0
    count =0
    ratio =0
    for k,v in pnDict.items():
        posTot += v[0]
        negTot += v[1]
        count+=1
    if negTot!=0:
        gen_pos = [posTot,negTot,float(posTot)/negTot,float(posTot)/count,float(negTot)/count]
    else:
        gen_pos = [posTot,negTot,None,float(posTot)/count,float(negTot)/count]
    return gen_pos

def auGovPosNeg(auDict,positiveWords,negativeWords):
    pnDict = dict()
    for k,v in auDict.items():
        negativePage = 0
        positivePage = 0
        rawPositive=0
        rawNegative=0
        ratio = 0
        pnArray =[]
        lineList =auDict[k].split('.')
        for i in range(len(lineList)):
            if 'government' in lineList[i]:
                wordList = lineList[i].split(' ')
                positiveCount=0
                negativeCount=0
                for j in range(len(wordList)):
                    if wordList[j].strip() in positiveWords:
                        positiveCount+=1
                        rawPositive+=1
                    if wordList[j].strip() in negativeWords:
                        negativeCount+=1
                        rawNegative+=1
                if negativeCount == 2:
                    positivePage+=1
                elif positiveCount>0 and negativeCount==0:
                    positivePage+=1
                elif negativeCount>0 and positiveCount==0:
                    negativePage+=1
                elif negativeCount>positiveCount:
                    negativePage+=1
                elif positiveCount>negativeCount:
                    positivePage+=1
                elif positiveCount==negativeCount and positiveCount!=0:
                    positivePage+=1 
        if rawNegative!=0:
            ratio = float(rawPositive)/rawNegative
        pnArray =[rawPositive,rawNegative,ratio,positivePage,negativePage]
        pnDict[k]=pnArray
    
    posTot=0
    negTot=0
    count =0
    ratio =0
    for k,v in pnDict.items():
        posTot += v[0]
        negTot += v[1]
        count+=1
    if negTot!=0:
        gov_pos = [posTot,negTot,float(posTot)/negTot,float(posTot)/count,float(negTot)/count]
    else:
        gov_pos = [posTot,negTot,None,float(posTot)/count,float(negTot)/count]
    return gov_pos

#find country counting
def countryCounter(auDict,caDict,ukDict):
    ausDict=dict()
    canDict =dict()
    unitedDict = dict()
    totalWordsau=0
    totalWordsca=0
    totalWordsuk=0

    for k,v in auDict.items():
        ausCount=0
        lineList =auDict[k].split('.')
        for i in range(len(lineList)):
            wordList = lineList[i].split(' ')
            for j in range(len(wordList)):
                if 'australia' in wordList[j].strip():
                    ausCount+=1
                totalWordsau+=1
        ausDict[k]=ausCount

    for k,v in caDict.items():
        canCount=0
        lineList =caDict[k].split('.')
        for i in range(len(lineList)):
            wordList = lineList[i].split(' ')
            for j in range(len(wordList)):
                if 'canada' in wordList[j].strip():
                    canCount+=1
                totalWordsca+=1
        canDict[k]=canCount

    for k,v in ukDict.items():
        ukCount=0
        lineList =ukDict[k].split('.')
        for i in range(len(lineList)):
            wordList = lineList[i].split(' ')
            for j in range(len(wordList)):
                if 'united kingdom' in wordList[j].strip():
                    ukCount+=1
                elif 'great britain' in wordList[j].strip():
                    ukCount+=1
                elif 'uk' in wordList[j].strip():
                    ukCount+=1
                totalWordsuk+=1
        unitedDict[k]=ukCount
    return ausDict,canDict,unitedDict,totalWordsau,totalWordsca,totalWordsuk

#find percentages
def percentageListCreator(ausDict,canDict,unitedDict,totalWordsau,totalWordsca,totalWordsuk):
    auWords =0
    for k,v in ausDict.items():
        auWords+=v
    caWords=0
    for k,v in canDict.items():
        caWords+=v
    ukWords=0
    for k,v in unitedDict.items():
        ukWords+=v
    percentageList =[float(auWords)/totalWordsau, float(caWords)/totalWordsca, float(ukWords)/totalWordsuk]
    percentageList = [val*100 for val in percentageList]
    return percentageList

#find domain occurances
def findauDomains(auDict):
    countDict=dict()
    for k,v in auDict.items():
        temp = urlparse(k).netloc
        if temp in countDict:
            countDict[temp]+=1
        else:
            countDict[temp]=1
    countList = []
    for k,v in countDict.items():
        tup=(k,v)
        countList.append(tup)
    return countList

#main method
def main(WARC_fname, positive_words_fname, negative_words_fname):
    htmlDict,responselist,htmllist = readWARC(WARC_fname)
    htmllist = formatHTML(htmllist)
    domainDict = cleanedDictCreator(htmllist, responselist)
    auDict,caDict,ukDict = countryDict(domainDict)
    positiveWords,negativeWords = posNegListCreator(positive_words_fname,negative_words_fname)
    
    gen_pos = auGenPosNeg(auDict,positiveWords,negativeWords)
    
    gov_pos = auGovPosNeg(auDict,positiveWords,negativeWords)
 
    ausDict,canDict,unitedDict,totalWordsau,totalWordsca,totalWordsuk = countryCounter(auDict,caDict,ukDict)
    
    pat = percentageListCreator(ausDict,canDict,unitedDict,totalWordsau,totalWordsca,totalWordsuk)
    
    top_links = findauDomains(auDict)
    
    return gen_pos,gov_pos,pat,top_links

if __name__=='__main__':
    gen_pos, gov_pos, pat, top_links=main('warc_sample_file.warc','positive_words.txt','negative_words.txt')
    print("gen_pos: ",gen_pos)
    print("gov_pos: ",gov_pos)
    print("pat: ",pat)
    print("top_links: ",top_links)






