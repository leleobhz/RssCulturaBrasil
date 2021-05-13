#!/usr/bin/python3

import urllib.request, re, datetime, subprocess, shlex, json, sys
from pytz import timezone
from bs4 import BeautifulSoup

# A bit of https://gist.github.com/oldo/dc7ee7f28851922cca09

def getInfoPrograma(programa):
    retorno = {}

    page='http://culturabrasil.cmais.com.br/programas/'+programa
    pageSobre='http://culturabrasil.cmais.com.br/programas/'+programa+'/sobre'

    try:
        htmlParsed = BeautifulSoup(urllib.request.urlopen(urllib.request.Request(url=page, headers={ 'User-Agent': 'Mozilla/5.0' })).read(), 'lxml')
    except:
        print('Programa não existente. Saindo')
        sys.exit(1)

    htmlSobreParsed = BeautifulSoup(urllib.request.urlopen(urllib.request.Request(url=pageSobre, headers={ 'User-Agent': 'Mozilla/5.0' })).read(), 'lxml')

    retorno['nome'] = list(list(htmlParsed.find_all('div', attrs={'class' : 'lista-assets span8'}))[0].find_all('h1'))[0].text
    retorno['descricao'] = list(list(htmlSobreParsed.find_all('div', attrs={'class' : 'content'}))[0].find_all('h2'))[0].text

    return retorno

def getEntries(programa):
    urlList=[]

    urlPages=('http://culturabrasil.cmais.com.br/programas/'+programa, 'http://culturabrasil.cmais.com.br/programas/'+programa+'/2')

    for page in urlPages:
        htmlParsed = BeautifulSoup(urllib.request.urlopen(urllib.request.Request(url=page, headers={ 'User-Agent': 'Mozilla/5.0' })).read(), 'lxml')

        allLink = htmlParsed.find_all('a', href=re.compile('http://culturabrasil.cmais.com.br/programas/'+programa+'/arquivo/'))

        for link in allLink:
            urlList.append(link.get('href'))
    return urlList


def parseEntry(page):

    entry={}
    htmlParsed = BeautifulSoup(urllib.request.urlopen(urllib.request.Request(url=page, headers={ 'User-Agent': 'Mozilla/5.0' })).read(), 'lxml')

    # Data
    entry['data'] = timezone('America/Sao_Paulo').localize(datetime.datetime.strptime(list(list(htmlParsed.find_all('div', attrs={'class' : 'row-fluid signature'}))[0].find_all('small'))[1].text.split(' - ', 1)[0], '%d/%m/%y %H:%M'))

    # Imagem
    entry['imagem'] = htmlParsed.find('img', src=re.compile('http://midia.cmais.com.br/assets/image/original/')).get('src')

    # Titulo
    entry['titulo'] = list(list(htmlParsed.find_all('div', attrs={'class' : 'content'}))[0].find_all('h1'))[0].text

    # Descricao
    entry['descricao'] = list(list(htmlParsed.find_all('div', attrs={'class' : 'content'}))[0].find_all('p'))[1].text

    # Audio
    entry['audio'] = re.search('http://midia.cmais.com.br/assets/audio/default/.*\.mp3',str(htmlParsed.find_all("div", {"class": "span8 content-asset"})[0])).group()

    # Tamanho do arquivo
    entry['filesize'] = urllib.request.urlopen(urllib.request.Request(url=entry['audio'], headers={ 'User-Agent': 'Mozilla/5.0' })).headers['content-length']

    # Duração
    # Based on https://gist.github.com/oldo/dc7ee7f28851922cca09

    entry['duracao']  = int(round(float(json.loads(subprocess.check_output(shlex.split("ffprobe -v quiet -print_format json -show_streams "+entry['audio'])).decode('utf-8'))['streams'][0]['duration'])))

    return entry

def feedGen(programa):
    from feedgen.feed import FeedGenerator

    infoPrograma=getInfoPrograma(programa)

    fg = FeedGenerator()
    fg.load_extension('podcast')
    fg.title('Rádio Cultura Brasil: '+infoPrograma['nome'])
    fg.podcast.itunes_author('Rádio Cultura Brasil')
    fg.description(infoPrograma['descricao'])
    fg.podcast.itunes_summary(infoPrograma['descricao'])
    fg.link(href='http://culturabrasil.cmais.com.br/programas/'+programa)
    fg.podcast.itunes_image('http://cmais.com.br/portal/images/capaPrograma/culturabrasil/logoam.png')
    fg.podcast.itunes_category({"cat":"Music","sub":"Music"})

    for entry in getEntries(programa):
        parsedEntry = parseEntry(entry)

        fe = fg.add_entry()
        fe.podcast.itunes_image(parsedEntry['imagem'])
        fe.link(href=parsedEntry['audio'], rel='enclosure')
        fe.title(parsedEntry['titulo'])
        fe.description(parsedEntry['descricao'])
        fe.podcast.itunes_summary(parsedEntry['descricao'])
        fe.enclosure(url=parsedEntry['audio'], length=parsedEntry['filesize'], type='audio/mpeg')
        fe.published(parsedEntry['data'])
        fe.podcast.itunes_duration(str(datetime.timedelta(seconds=parsedEntry['duracao'])))

    fg.rss_file('/tmp/'+programa+'.rss')
    #return fg.rss_str(pretty=True)


if __name__ == "__main__":
    for programa in sys.argv[1:]:
        feedGen(programa)

