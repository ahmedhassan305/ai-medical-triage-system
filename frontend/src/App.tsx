import HomePage from "./pages/HomePage";
import { LanguageProvider } from "./i18n/LanguageProvider";

function App() {
  return (
    <LanguageProvider>
      <HomePage />
    </LanguageProvider>
  );
}

export default App;
