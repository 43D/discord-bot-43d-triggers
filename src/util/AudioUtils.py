import mutagen

def get_audio_duration(filepath: str) -> float:
    try:
        audio = mutagen.File(filepath) # type: ignore
        if audio is not None and hasattr(audio.info, 'length'):
            return audio.info.length
        print("No audio, tamanho desconecido, usando fallback de 30s")
        return 30.0
    except Exception as e:
        print(f"Erro ao obter duração do áudio {filepath}: {e}")
        return 30.0