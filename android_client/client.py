import asyncio
import threading
import websockets
import logging

logger = logging.getLogger(__name__)

class WSClient:
    def __init__(self, on_message, on_connect=None):
        self.on_message = on_message
        self.on_connect = on_connect
        self._loop = None
        self._ws = None
        self._thread = None
        self._ready = threading.Event()

    def connect(self, uri: str):
        # Если есть живой поток — сначала корректно закрываем
        if self._thread and self._thread.is_alive():
            self.disconnect()

        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                # Запускаем подключение
                self._loop.run_until_complete(self._connect_async(uri))
                # Если сокет открыт — крутим цикл
                if self._ws:
                    self._loop.run_forever()
            except Exception as e:
                logger.error(f"Event loop error: {e}")
            finally:
                self._cleanup()

        self._thread = threading.Thread(target=run_loop, daemon=True, name="WS-Client")
        self._thread.start()
        self._ready.wait(timeout=5.0)  # Ждём установки соединения

    async def _connect_async(self, uri: str):
        try:
            self._ws = await websockets.connect(uri)
            self._ready.set()
            if self.on_connect:
                self._loop.call_soon_threadsafe(self.on_connect)
            self._loop.create_task(self._listen())
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._ready.set()

    async def _listen(self):
        try:
            async for message in self._ws:
                if self.on_message:
                    try:
                        self.on_message(message)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
        except websockets.ConnectionClosed:
            logger.info("WebSocket closed by server.")
        except Exception as e:
            logger.error(f"Listen error: {e}")

    def send(self, message: str):
        if self._loop and self._loop.is_running() and self._ws:
            try:
                asyncio.run_coroutine_threadsafe(self._ws.send(message), self._loop)
            except Exception:
                pass

    def disconnect(self):
        """Корректное закрытие соединения"""
        if self._loop and self._ws:
            # 1. Закрываем сокет (асинхронно в потоке)
            try:
                asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)
            except Exception:
                pass
            
            # 2. Останавливаем цикл (асинхронно)
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
            
            # 3. Ждём завершения потока (не даём GUI зависнуть надолго)
            self._thread.join(timeout=2.0)
        
        # 4. Сбрасываем состояние
        self._ws = None
        self._loop = None
        self._thread = None
        self._ready.clear()

    def _cleanup(self):
        """Очистка висящих задач и закрытие цикла"""
        if self._loop:
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            self._loop.close()
            self._loop = None
            self._ws = None
            self._ready.clear()