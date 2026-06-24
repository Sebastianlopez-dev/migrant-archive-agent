import './styles.css';
import { ChatWidget } from './chat-widget.ts';

function bootstrap(): void {
  const root = document.getElementById('chat-root');
  if (root) {
    new ChatWidget(root);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap);
} else {
  bootstrap();
}
