#!/usr/bin/env python
# coding: utf-8

# In[1]:


import re
import operator
from io import StringIO
from html.parser import HTMLParser
import string
from urllib.parse import urlparse
#from unidecode import unidecode
#from nltk.tokenize import word_tokenize


# In[2]:


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
            if '<!DOCTYPE' in line or '<html' in line:
                boolDoctype = True
            if boolDoctype == True:
                temp+=line.strip()
    #print(htmllist[0])    
    return htmlDict,responselist,htmllist


# In[3]:


#tokenize the words
def word_tokenize(sentence):
    return [word.lower() for word in sentence.split()]

# removes a list of unwanted words from a tokenized list
def removeWords(listOfTokens, listOfWords):
    return [token for token in listOfTokens if token not in listOfWords]

# remove punctations
def removePunctuations(listOfTokens):
    test_joined=' '.join(listOfTokens)
    punc = string.punctuation
    punc = punc.replace('.','')
    punc = punc.replace('+','')
    punc = punc.replace('-','')
    punc = punc.replace('*','')
    
    translator = re.compile('[%s]' % re.escape(punc))
    test_punc_removed=translator.sub(' ', test_joined)
    
    test_punc_removed=re.sub(' +',' ',test_punc_removed).strip()
    test_punc_removed_join=test_punc_removed

    return [word for word in test_punc_removed_join.split()]

# removes any words composed of less than 2
def twoLetters(listOfTokens):
    twoLetterWord = []
    twoLetterList =['a','i','a+','am','an','as','at','by','do','go','he','hi','if','is','in','it','me','my','no',
                    'of','ok','on','or','ox','pi','so','to''up','us','we']
    for token in listOfTokens:
        if (len(token) <= 2) and (token not in twoLetterList) :
            twoLetterWord.append(token)
    return twoLetterWord


# In[4]:


#format HTML
def formatHTML(htmllist):
    pattern1 = r"(?is)(<script[^>]*>)(.*?)(</script>)"
    pattern2 = r"(?is)(<style[^>]*>)(.*?)(</style>)"
    pattern3 = r"(?is)(<title[^>]*>)(.*?)(</title>)"
    for i in range(len(htmllist)):

        #remove script tags
        htmllist[i] = re.sub(pattern1,' ',htmllist[i])
        #remove style tags
        htmllist[i] = re.sub(pattern2,' ',htmllist[i])
        #remove title tag
        htmllist[i] = re.sub(pattern3,' ',htmllist[i])
        #strip out html tags
        htmllist[i] = re.sub(r'<.+?>', ' ', htmllist[i])
        htmllist[i] = re.sub(r'&.+?;', ' ', htmllist[i])

        #remove special characters and leave only words
        htmllist[i]=re.sub('\W_',' ', htmllist[i])

        # removes numbers and words concatenated with numbers IE h4ck3r. Removes road names such as BR-381.
        #htmllist[i]=re.sub("\S*\d\S*"," ", htmllist[i])
        htmllist[i]=''.join([t for t in htmllist[i] if not t.isdigit()])
            
        htmllist[i] = htmllist[i].replace(',', '.')          # Replace commas with period for split
        htmllist[i] = htmllist[i].replace('?', '.')          # Replace question marks with periods for split
        htmllist[i] = htmllist[i].rstrip('\n')               # Removes line breaks
        htmllist[i] = htmllist[i].casefold()                 # Makes all letters lowercase

        #remove unwanted two letter words
        listOfTokens = word_tokenize(htmllist[i])
        twoLetterWord = twoLetters(listOfTokens)
        listOfTokens = removeWords(listOfTokens, twoLetterWord)

        listOfTokens = removePunctuations(listOfTokens)
        
        #remove two letter words after removing punctuations
        twoLetterWord = twoLetters(listOfTokens)
        listOfTokens = removeWords(listOfTokens, twoLetterWord)
    
        htmllist[i]   = " ".join(listOfTokens)
        
    return htmllist


# In[5]:


#create a cleaned dict
def cleanedDictCreator(htmllist, responselist):
    domainDict = dict()
    domainOnly =[]
    for i in range(len(responselist)):
        domain = urlparse(responselist[i]).netloc
        domainOnly.append(domain)
        domainDict[responselist[i]] = htmllist[i]
    return domainDict


# In[6]:


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


# In[7]:


#positive and negative list creation
def posNegListCreator(posText,negText):
    positiveWords = [line.rstrip('\n') for line in open(posText)]
    negativeWords =[line.rstrip('\n') for line in open(negText)]
    return positiveWords,negativeWords


# In[8]:


#find positive and negative words in .au domains
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
                negativePage+=0
            elif positiveCount>negativeCount:
                positivePage+=0
            elif positiveCount==negativeCount and positiveCount!=0:
                positivePage+=0 
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


# In[9]:


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
                    negativePage+=0
                elif positiveCount>negativeCount:
                    positivePage+=0
                elif positiveCount==negativeCount and positiveCount!=0:
                    positivePage+=0 
        if rawNegative!=0:
            ratio = float(rawPositive)/rawNegative
        pnArray =[rawPositive,rawNegative,ratio,positivePage,negativePage]
        pnDict[k]=pnArray
    
    posTot=0
    negTot=0
    count =0
    ratio =0
    for k,v in pnDict.items():
        posTot += v[3]
        negTot += v[4]
        count+=1
    if negTot!=0:
        gov_pos = [posTot,negTot,float(posTot)/negTot,float(posTot)/count,float(negTot)/count]
    else:
        gov_pos = [posTot,negTot,None,float(posTot)/count,float(negTot)/count]
    return gov_pos


# In[10]:


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


# In[11]:


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


# In[12]:


#find domain occurances in the dict
def findauDomains(auDict):
    countDict=dict()
    for k,v in auDict.items():
        temp = urlparse(k).netloc
        if temp in countDict:
            countDict[temp]+=1
        else:
            countDict[temp]=1
    cDict = dict(sorted(countDict.items(),key=operator.itemgetter(1),reverse=True))
    countList=[]
    for k,v in cDict.items():
        tup=(k,v)
        countList.append(tup)
    return countList[:5]


# In[13]:


#find the domain occurances in the file
def findauDomainsinFile(filename):
    f = open(filename)
    rawVal=[]
    l=[]
    for line in f:
        s = re.findall(r'(https?://\S+)', line)
        if s is not None:
            for k in s:
                m = re.search('https?://([A-Za-z_0-9.-]+).*',k)
                if m:
                    rawVal.append(m.group(1))
    for k in range(len(rawVal)):
        temp =rawVal[k].split('.')
        if temp[len(temp)-1].strip()=='au':
            l.append(rawVal[k])
    countDict=dict()
    for i in range(len(l)):
        if l[i] in countDict:
            countDict[l[i]]+=1
        else:
            countDict[l[i]]=1
    cDict = dict(sorted(countDict.items(),key=operator.itemgetter(1),reverse=True))
    countList=[]
    for k,v in cDict.items():
        tup=(k,v)
        countList.append(tup)
    return countList[:5]


# In[14]:


#main method
def main(WARC_fname, positive_words_fname, negative_words_fname):
    try:
        htmlDict,responselist,htmllist = readWARC(WARC_fname)
        htmllist = formatHTML(htmllist)
        domainDict = cleanedDictCreator(htmllist, responselist)
        auDict,caDict,ukDict = countryDict(domainDict)

        positiveWords,negativeWords = posNegListCreator(positive_words_fname,negative_words_fname)

        gen_pos = auGenPosNeg(auDict,positiveWords,negativeWords)

        gov_pos = auGovPosNeg(auDict,positiveWords,negativeWords)

        ausDict,canDict,unitedDict,totalWordsau,totalWordsca,totalWordsuk = countryCounter(auDict,caDict,ukDict)

        pat = percentageListCreator(ausDict,canDict,unitedDict,totalWordsau,totalWordsca,totalWordsuk)

        top_links =findauDomainsinFile(WARC_fname)
        
        return gen_pos,gov_pos,pat,top_links
    except Exception as e:
        print(str(e))
        return ([],[],[],dict())
        


# In[15]:


#if __name__=='__main__':
#    gen_pos, gov_pos, pat, top_links=main('warc_sample_file.warc','positive_words.txt','negative_words.txt')
#    print("gen_pos: ",gen_pos)
#    print("gov_pos: ",gov_pos)
#    print("pat: ",pat)
#    print("top_links: ",top_links)


# In[16]:


#TEST1

#try:
#    answer,b,c,d = main("warc_sample_file.warc","positive_words.txt","negative_words.txt")
#    sample_answer = [1238, 586, 2.1126, 26.913, 12.7391]
#    print(a,b,c,d)
#    flag = True
#    if len(answer) != len(sample_answer):
#        flag = False
#    if abs(answer[0]-sample_answer[0]) > 1 or abs(answer[1]-sample_answer[1]) > 1 or abs(answer[2]-sample_answer[2]) > 0.001 or abs(answer[3]-sample_answer[3]) > 0.001 or abs(answer[4]-sample_answer[4]) > 0.001:
#        flag = False
#    print(flag)
#except Exception as e:
#    print("Error:",str(e))
#    print(False)

#(RESULT = True)


# In[17]:


#TEST2

# try:
#    a,answer,c,d = main("warc_sample_file.warc","positive_words.txt","negative_words.txt")
#    sample_answer = [21, 13, 1.6154, 0.4565, 0.2826]
#    flag = True
#    if len(answer) != len(sample_answer):
#       flag = False
#    if abs(answer[0]-sample_answer[0]) > 1 or abs(answer[1]-sample_answer[1]) > 1 or abs(answer[2]-sample_answer[2]) > 0.001 or abs(answer[3]-sample_answer[3]) > 0.001 or abs(answer[4]-sample_answer[4]) > 0.001:
#       flag = False
#    print(flag)
# except Exception as e:
#    print("Error:",str(e))
#    print(False)

#(RESULT = True)


# In[18]:


#TEST3

# try:
#    a,b,answer,d = main("warc_sample_file.warc","positive_words.txt","negative_words.txt")
#    sample_answer = [0.3421, 0.3186, 0.0995]
#    flag = True
#    if len(answer) != len(sample_answer):
#       flag = False
#    if abs(answer[0]-sample_answer[0]) > 0.001 or abs(answer[1]-sample_answer[1]) > 0.001 or abs(answer[2]-sample_answer[2]) > 0.001:
#       flag = False
#    print(flag)
# except Exception as e:
#    print("Error:",str(e))
#    print(False)

#(RESULT = True)


# In[19]:


#TEST4
   
# try:
#    a,b,c,answer = main("warc_sample_file.warc","positive_words.txt","negative_words.txt")
#    sample_answer = [('www.industryupdate.com.au', 275), ('religionsforpeaceaustralia.org.au', 183), ('boundforsouthaustralia.history.sa.gov.au', 148), ('www.jcu.edu.au', 114), ('blogs.geelongcollege.vic.edu.au', 54)]
#    flag = True
#    if len(answer) != len(sample_answer):
#       flag = False
#    for i in range(len(answer)):
#       if answer[i][0] != sample_answer[i][0] or answer[i][1] != sample_answer[i][1]:
#          flag = False
#    print(flag)
# except Exception as e:
#    print("Error:",str(e))
#    print(False)
   
#(RESULT = True)


# In[ ]:




