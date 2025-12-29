def build_summary(user_msg, agent_reply):
    return { 'pedido_o_consulta': user_msg, 'accion_del_agente': agent_reply, 'proximos_pasos': 'Enviar cotización o escalar al asesor humano.' }
