 const lines = [
        "I only act as an operator.",
        "I do not intervene in any way.",
        "I do not think.",
        "I do not complain.",
        "I react.",
        "I follow.",
        "I measure.",
        "I observe.",
        "I follow instructions.",
        "I am dependent.",
        "I am mobile.",
        "I listen.",
        "I am passive.",
        "I am the one who is guided.",
        "I do not function without him.",
        "I undergo.",
        "I have a veto for Illegal trespassing."
    ];

function startRandomText() {
    const container = document.getElementById('text-lines');
    setInterval(() => {
        const randomLine = lines[Math.floor(Math.random() * lines.length)];
        container.innerHTML = randomLine;
    }, 1000);
}

startRandomText();