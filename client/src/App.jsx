import { useEffect, useState } from "react";
import { socket } from "./lib/socket.js";
import Home from "./screens/Home.jsx";
import Lobby from "./screens/Lobby.jsx";
import Game from "./screens/Game.jsx";
import RoundResult from "./screens/RoundResult.jsx";
import Final from "./screens/Final.jsx";

export default function App() {
  const [screen, setScreen] = useState("home");
  const [room, setRoom] = useState(null);
  const [roundData, setRoundData] = useState(null);
  const [resultData, setResultData] = useState(null);
  const [finalData, setFinalData] = useState(null);
  const [error, setError] = useState("");
  const [mySid, setMySid] = useState(null);

  useEffect(() => {
    const onConnect = () => setMySid(socket.id);
    const onCreated = ({ code }) => {
      setScreen("lobby");
    };
    const onJoined = ({ code }) => {
      setScreen("lobby");
    };
    const onUpdate = (r) => setRoom(r);
    const onPlaylist = () => {};
    const onRoundStart = (data) => {
      setRoundData(data);
      setResultData(null);
      setScreen("game");
    };
    const onRoundEnd = (data) => {
      setResultData(data);
      setScreen("result");
    };
    const onGameEnd = (data) => {
      setFinalData(data);
      setScreen("final");
    };
    const onError = ({ message }) => {
      setError(message);
      setTimeout(() => setError(""), 4000);
    };

    socket.on("connect", onConnect);
    socket.on("room:created", onCreated);
    socket.on("room:joined", onJoined);
    socket.on("room:update", onUpdate);
    socket.on("playlist:update", onPlaylist);
    socket.on("round:start", onRoundStart);
    socket.on("round:end", onRoundEnd);
    socket.on("game:end", onGameEnd);
    socket.on("error", onError);

    if (socket.connected) setMySid(socket.id);

    return () => {
      socket.off("connect", onConnect);
      socket.off("room:created", onCreated);
      socket.off("room:joined", onJoined);
      socket.off("room:update", onUpdate);
      socket.off("playlist:update", onPlaylist);
      socket.off("round:start", onRoundStart);
      socket.off("round:end", onRoundEnd);
      socket.off("game:end", onGameEnd);
      socket.off("error", onError);
    };
  }, []);

  const isHost = room && mySid && room.host === mySid;

  const playAgain = () => {
    socket.emit("game:reset", { code: room.code });
    setScreen("lobby");
    setRoundData(null);
    setResultData(null);
    setFinalData(null);
  };

  return (
    <div className="min-h-screen w-full">
      {error && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-full bg-red-500/90 text-white text-sm shadow-lg animate-pop">
          {error}
        </div>
      )}
      {screen === "home" && <Home />}
      {screen === "lobby" && room && (
        <Lobby room={room} isHost={isHost} mySid={mySid} />
      )}
      {screen === "game" && roundData && room && (
        <Game
          room={room}
          roundData={roundData}
          isHost={isHost}
          mySid={mySid}
        />
      )}
      {screen === "result" && resultData && room && (
        <RoundResult
          room={room}
          result={resultData}
          isHost={isHost}
          mySid={mySid}
        />
      )}
      {screen === "final" && finalData && room && (
        <Final
          room={room}
          finalData={finalData}
          isHost={isHost}
          onPlayAgain={playAgain}
        />
      )}
    </div>
  );
}
