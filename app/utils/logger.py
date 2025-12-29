import json, os
from datetime import datetime
LOG_FILE = os.path.join('logs','chat_history.json')
def log_interaction(session_id, user_msg, agent_reply, channel='unknown'):
    os.makedirs('logs', exist_ok=True)
    record = {'timestamp': datetime.now().isoformat(), 'session_id': session_id, 'channel': channel, 'cliente': user_msg, 'agente': agent_reply}
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump([record], f, ensure_ascii=False, indent=2)
    else:
        with open(LOG_FILE, 'r+', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception:
                data = []
            data.append(record)
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=2)
