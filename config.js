// Configuração do app. Preencha com os dados do seu projeto Firebase (Configurações do projeto > Seus apps > Web).
// Esses valores não são secretos: o acesso é protegido pelas regras do Firestore (firestore.rules).
window.APP_CONFIG = {
  firebase: {
    apiKey: "",
    authDomain: "",
    projectId: "",
    appId: ""
  },
  // Endereço do serviço que avalia a foto da refeição (pasta worker/). Vazio = botão de foto escondido.
  photoApi: ""
};
