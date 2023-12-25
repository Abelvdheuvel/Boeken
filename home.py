import streamlit as st
from deta import Deta
from bs4 import BeautifulSoup
import requests
import pandas as pd
import datetime
import altair as alt

def connect_db():
    deta = Deta(st.secrets["data_key"])
    db = deta.Base("boeken")
    return db

def bookPageScraper(url):
    page = requests.get(url)

    soup = BeautifulSoup(page.content, 'html.parser')
    mainContent = soup.find(id='mainContent')

    images = soup.find_all("img", class_="js_selected_image")
    imageLink = images[0].get('src')

    if "noimage_" in imageLink:
        imageLink = 'Images/no-image.png'

    titleBook = soup.find("span", attrs={"data-test": "title"}).text

    specs_name = mainContent.find_all('dt', class_="specs__title")
    specs_values = mainContent.find_all('dd', class_="specs__value")
    specListTitles = []
    specListValues = []
    for title, value in zip(specs_name, specs_values):
        specListTitles.append(title.text.strip())
        specListValues.append(value.text.strip())

    df = pd.DataFrame(index=specListTitles, data=specListValues, columns=['Value'])
    df = df[~df.index.duplicated(keep='last')]

    try:
        newEntry = dict(zip(['Naam', 'Auteur', 'Sterren', 'Taal', 'Begin Datum', 'Eind datum',
                        'Genre', 'Uitgeef datum', 'Aantal Paginas'],
                        [titleBook, df.loc['Hoofdauteur'].Value, '5', df.loc['Taal'].Value,
                            '18-11-2000', '18-11-2000', df.loc['Categorieën'].Value.split('\n')[0],
                            df.loc['Oorspronkelijke releasedatum'].Value, df.loc['Aantal pagina\'s'].Value]
                        ))
        return newEntry, imageLink
    
    except KeyError:
        st.error('❌ Kan geen boek met deze titel vinden')
        return '-', '-'
    

def new_book_info(NewBookDict, imageLink):
    col1, col2 = st.columns(2)
    with col1:
        st.image(imageLink, width=200)
    with col2:
        st.subheader(NewBookDict['Naam'])
        st.markdown('Auteur: ' + NewBookDict['Auteur'])
        st.markdown('Aantal Paginas: ' + NewBookDict['Aantal Paginas'])
        st.markdown('Taal: ' + NewBookDict['Taal'])
        st.markdown('Release datum: ' + NewBookDict['Uitgeef datum'])

    st.markdown('Hoeveel sterren geef je het boek?')
    rating = st.radio('Aantal sterren', ['⭐', '⭐⭐', '⭐⭐⭐', '⭐⭐⭐⭐', '⭐⭐⭐⭐⭐'], index=3, horizontal=True)

    col3, col4 = st.columns(2)
    with col3:
        beginDate = st.date_input('Begin datum')
    with col4:
        endDate = st.date_input('Eind datum')

    return rating, beginDate, endDate

def bookNameTransform(bookName):
    bookNameUrl = bookName.replace(' ', '+').lower()
    url = 'https://www.bol.com/nl/nl/s/?page=1&searchtext=' + bookNameUrl #+ '&view=list&N=8299'

    searchPage = requests.get(url)

    soupResults = BeautifulSoup(searchPage.content, 'html.parser')
    mainSearchContent = soupResults.find_all("a", class_="product-title px_list_page_product_click list_page_product_tracking_target")

    return mainSearchContent

def manualInput(db):
    with st.expander('Klik voor handmatige invoer'):
        with st.form('manualinput'):
            title = st.text_input('Titel')
            author = st.text_input('Auteur')
            rating = st.radio('Aantal sterren', ['⭐', '⭐⭐', '⭐⭐⭐', '⭐⭐⭐⭐', '⭐⭐⭐⭐⭐'], index=3, horizontal=True)
            language = st.radio('Taal', ['Nederlands', 'Engels'])
            beginDate = st.date_input('Begin datum')
            endDate = st.date_input('Eind datum')
            genre = st.text_input('Genre')
            releaseDate = st.text_input('Uitgeef datum')
            pages = st.text_input('Aantal paginas')

            manualSubmit = st.form_submit_button()
        if manualSubmit:
            newEntry = dict(zip(['Naam', 'Auteur', 'Sterren', 'Taal', 'Begin Datum', 'Eind datum',
                                'Genre', 'Uitgeef datum', 'Aantal Paginas'],
                                [title, author, rating, language,
                                str(beginDate), str(endDate), genre,
                                releaseDate,
                                pages]
                                ))
            
            return newEntry

def graphs(df):
    st.subheader("Grafieken")

    dfGrouped = df.copy(deep=True)
    dfGrouped['Eind datum'] = pd.to_datetime(dfGrouped['Eind datum'], yearfirst=True)
    dfGrouped['Begin Datum'] = pd.to_datetime(dfGrouped['Begin Datum'], yearfirst=True)
    dfGrouped['Aantal Paginas'] = dfGrouped['Aantal Paginas'].astype(int)

    ganttChart = alt.Chart(dfGrouped.sort_values(by='Begin Datum')).mark_bar().encode(
        x=alt.X('Begin Datum', sort='ascending'),
        x2='Eind datum',
        y=alt.Y('Naam', sort=None)
    ).configure_mark(color='#ff4b4b')

    dfGrouped['Eind datum'] = pd.to_datetime(df['Eind datum'])
    dfGrouped = dfGrouped.set_index('Eind datum')

    dfCount = dfGrouped.groupby(pd.Grouper(freq='M')).count()
    dfCount.rename(columns={'Aantal Paginas': 'Aantal Boeken'}, inplace=True)
    dfCount['month'] = dfCount.index.to_period('M').astype(str)

    dfPages = dfGrouped.groupby(pd.Grouper(freq='M')).sum()
    dfPages['month'] = dfPages.index.to_period('M').astype(str)

    monthChart = alt.Chart(dfCount).mark_bar().encode(
        x=alt.X('month', sort=None),
        y='Aantal Boeken'
    ).configure_mark(color='#ff4b4b')


    pagesChart = alt.Chart(dfPages).mark_bar().encode(
        x=alt.X('month', sort=None),
        y='Aantal Paginas'
    ).configure_mark(color='#ff4b4b')

    st.write('Aantal Boeken per Maand')
    st.altair_chart(monthChart, use_container_width=True)
    st.write('Aantal Pagina\'s per Maand')
    st.altair_chart(pagesChart, use_container_width=True)
    st.write('Tijdsduur per boek')
    st.altair_chart(ganttChart, use_container_width=True)


def main():
    st.title('Boeken')

    db = connect_db()

    bookName = st.text_input('Welk boek heb je gelezen?')
    if bookName:
        with st.form("form", clear_on_submit=True):
            submitted = st.form_submit_button("Store in database")
            mainSearchContent = bookNameTransform(bookName)
            book_dict, imageLink = bookPageScraper('https://www.bol.com' + mainSearchContent[0].get('href'))
            if book_dict == '-':
                bookName = False 
            else:
                rating, beginDate, endDate = new_book_info(book_dict, imageLink)    
            

        if submitted:
            book_dict['Begin Datum'] = str(beginDate)
            book_dict['Eind datum'] = str(endDate)
            book_dict['Sterren'] = str(rating)
            
            db.put(book_dict)
            bookName = False
            st.experimental_rerun()

    db_content = db.fetch().items

    df_boeken = pd.DataFrame(db_content)

    # for key in df_boeken.key:
    #     expire_at = datetime.datetime.now()
    #     db.update(None, key, expire_at=expire_at)
    st.table(df_boeken)

    graphs(df_boeken)

    st.subheader('Handmatige invoer')
    newEntry = False
    newEntry = manualInput(db)
    if newEntry:
        db.put(newEntry)

    st.subheader('Verwijder boeken')
    
    with st.form('deletebooks'):
        book_to_delete = st.selectbox('Welk boek wil je verwijderen', df_boeken['Naam'])

        submitted_to_delete = st.form_submit_button('Boek verwijderen')

    if submitted_to_delete:
        key_to_delete = str(df_boeken[df_boeken['Naam'] == book_to_delete]['key'].values[0])
        expire_at = datetime.datetime.now()
        db.update(None, str(key_to_delete), expire_at=expire_at)
        st.experimental_rerun()



if __name__ == '__main__':
    main()