/**
 * Configuración oficial de Firebase SDK para Vita Record / ÍntimaSalud.
 */

export const firebaseConfig = {
  apiKey: 'AIzaSyB9B72DuC0V3WJiDVFQ2be3aQrcA3XJMhs',
  authDomain: 'vita-record.firebaseapp.com',
  projectId: 'vita-record',
  storageBucket: 'vita-record.firebasestorage.app',
  messagingSenderId: '398180197268',
  appId: '1:398180197268:web:9d3bf990f78e30aa0b2581',
  measurementId: 'G-6C94W2CQYT'
}

export default ({ app }) => {
  // Configuración expuesta globalmente en la instancia de Vue
  app.config.globalProperties.$firebaseConfig = firebaseConfig
}
