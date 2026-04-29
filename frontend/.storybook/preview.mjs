import { setup } from '@storybook/vue3'
import { Quasar } from 'quasar'
import '@quasar/extras/material-icons/material-icons.css'
import 'quasar/src/css/index.sass'

setup((app) => {
  app.use(Quasar, { plugins: {} })
})

export default {
  parameters: {
    actions: { argTypesRegex: '^on[A-Z].*' },
    controls: { matchers: { color: /(background|color)$/i, date: /Date$/i } }
  }
}
