import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import Backend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    supportedLngs: ['zh-CN', 'en-US'],
    fallbackLng: 'zh-CN',
    debug: true,
    
    interpolation: {
      escapeValue: false, 
    },
    
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },

    detection: {
        order: ['localStorage', 'navigator'],
        lookupLocalStorage: 'app_language',
        caches: ['localStorage'],
    },

    react: {
        useSuspense: true
    }
  });

export default i18n;