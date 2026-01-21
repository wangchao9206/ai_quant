import React, { createContext, useContext, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

const LanguageContext = createContext();

export const LanguageProvider = ({ children }) => {
    const { t, i18n } = useTranslation();
    const [language, setLanguageState] = useState(i18n.language);

    useEffect(() => {
        const handleLanguageChanged = (lng) => {
            setLanguageState(lng);
        };

        i18n.on('languageChanged', handleLanguageChanged);

        // Initial sync if needed
        if (i18n.language !== language) {
            setLanguageState(i18n.language);
        }

        return () => {
            i18n.off('languageChanged', handleLanguageChanged);
        };
    }, [i18n, language]);

    const setLanguage = (lang) => {
        i18n.changeLanguage(lang);
    };

    return (
        <LanguageContext.Provider value={{ language, setLanguage, t }}>
            {children}
        </LanguageContext.Provider>
    );
};

export const useLanguage = () => useContext(LanguageContext);
