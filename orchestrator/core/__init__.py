# Orquestador CORE — Colbun S.A.
# Cuatro componentes que implementan la máquina de estados:
#   InstanceManager      → ciclo de vida de instancias
#   StateEngine          → valida y ejecuta transiciones
#   TransitionLogic      → lógica pura: siguiente nodo + actor
#   NotificationDispatcher → activa al siguiente actor
