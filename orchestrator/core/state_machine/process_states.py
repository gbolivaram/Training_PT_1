"""
Máquina de estados a nivel de PROCESO.
Define los estados válidos y las transiciones permitidas.
"""


class ProcessStates:
    EN_CURSO = "EN_CURSO"
    BLOQUEADO = "BLOQUEADO"
    COMPLETADO = "COMPLETADO"
    RECHAZADO = "RECHAZADO — ESCALAR A MANTENIMIENTO"
    DETENIDO = "DETENIDO — REQUIERE INTERVENCIÓN"

    # Estados terminales: el proceso no puede salir de estos
    TERMINAL = {COMPLETADO, RECHAZADO, DETENIDO}


# Transiciones válidas: estado_actual → {estados posibles}
VALID_TRANSITIONS = {
    ProcessStates.EN_CURSO: {
        ProcessStates.EN_CURSO,        # avanza nodo pero sigue en curso
        ProcessStates.BLOQUEADO,       # bloqueo por impedimento
        ProcessStates.COMPLETADO,      # llega a END_OK
        ProcessStates.RECHAZADO,       # llega a END_RECHAZO
        ProcessStates.DETENIDO,        # STOP o END_STOP
    },
    ProcessStates.BLOQUEADO: {
        ProcessStates.EN_CURSO,        # se desbloquea
    },
    # Los estados terminales no tienen transiciones de salida
}


class ProcessStateMachine:
    """Valida y ejecuta transiciones de estado a nivel de proceso."""

    @staticmethod
    def can_transition(current: str, target: str) -> bool:
        allowed = VALID_TRANSITIONS.get(current, set())
        return target in allowed

    @staticmethod
    def validate_transition(current: str, target: str) -> None:
        if not ProcessStateMachine.can_transition(current, target):
            raise InvalidTransitionError(
                f"Transición inválida: '{current}' → '{target}'"
            )

    @staticmethod
    def is_terminal(estado: str) -> bool:
        return estado in ProcessStates.TERMINAL

    @staticmethod
    def is_active(estado: str) -> bool:
        return estado == ProcessStates.EN_CURSO


class InvalidTransitionError(Exception):
    pass
