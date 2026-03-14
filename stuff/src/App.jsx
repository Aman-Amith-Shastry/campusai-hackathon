import { useState, useEffect } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import './App.css'

function GoalsPage() {
    const [goals, setGoals] = useState([])
    const [newGoal, setNewGoal] = useState('')
    const [suggestedMajor, setSuggestedMajor] = useState('')
    const [extractedKeywords, setExtractedKeywords] = useState([])
    const [suggestedElectives, setSuggestedElectives] = useState([])

    useEffect(() => {
        fetchGoals()
    }, [])

    const fetchGoals = async () => {
        try {
            const response = await fetch('http://localhost:8000/goals')
            const data = await response.json()
            setGoals(data)
        } catch (error) {
            console.error('Error fetching goals:', error)
        }
    }

    const addGoal = async (e) => {
        e.preventDefault()
        if (newGoal.trim()) {
            try {
                const response = await fetch('http://localhost:8000/goals', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ text: newGoal }),
                })
                const data = await response.json()
                setNewGoal('')
                setSuggestedMajor(data.suggested_major)
                setExtractedKeywords(data.keywords || [])
                setSuggestedElectives(data.electives?.electives || [])
                fetchGoals()
            } catch (error) {
                console.error('Error adding goal:', error)
            }
        }
    }

    return (
        <div className="app">
            <header>
                <h1>Long-Term Semester Planner</h1>
                <p>What are your goals and career aspirations?</p>
            </header>
            <main>
                <form onSubmit={addGoal}>
                    <label htmlFor="newGoal">What are your goals?</label>
                    <textarea
                        id="newGoal"
                        value={newGoal}
                        onChange={(e) => setNewGoal(e.target.value)}
                        placeholder="Enter your goal here..."
                        rows="3"
                    />
                    <button type="submit">Add Goal</button>
                </form>
                {suggestedMajor && (
                    <div className="suggestion">
                        <p>Suggested Major: <strong>{suggestedMajor}</strong></p>
                        {extractedKeywords.length > 0 && (
                            <p>
                                <strong>Extracted Keywords:</strong> {extractedKeywords.join(', ')}
                            </p>
                        )}
                        {suggestedElectives.length > 0 && (
                            <div>
                                <strong>Suggested Electives:</strong>
                                <ul>
                                    {suggestedElectives.map((elective, index) => (
                                        <li key={index}>{elective}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}
                {goals.length > 0 && (
                    <div className="goals-display">
                        <h2>Your Goals:</h2>
                        <ul>
                            {goals.map((goal, index) => (
                                <li key={index}>{goal}</li>
                            ))}
                        </ul>
                        <nav>
                            <Link to="/plan">View 8 Semester Plan</Link>
                        </nav>
                    </div>
                )}
            </main>
        </div>
    )
}

function PlanPage() {
    const [plan, setPlan] = useState([])
    const [currentSemester, setCurrentSemester] = useState(0)
    const [direction, setDirection] = useState('')

    useEffect(() => {
        fetchPlan()
    }, [])

    const fetchPlan = async () => {
        try {
            const response = await fetch('http://localhost:8000/plan')
            const data = await response.json()
            setPlan(data)
        } catch (error) {
            console.error('Error fetching plan:', error)
        }
    }

    const nextSemester = () => {
        setDirection('left')
        setCurrentSemester((prev) => (prev + 1) % plan.length)
    }

    const prevSemester = () => {
        setDirection('right')
        setCurrentSemester((prev) => (prev - 1 + plan.length) % plan.length)
    }

    return (
        <div className="app">
            <header>
                <h1>Your 8 Semester Plan</h1>
                <nav>
                    <Link to="/">Back to Goals</Link>
                </nav>
            </header>
            <main>
                {plan.length > 0 ? (
                    <div className="slideshow">
                        <div key={currentSemester} className={`semester ${direction}`}>
                            <h2>{plan[currentSemester].semester}</h2>
                            <p>{plan[currentSemester].description}</p>
                            <ul>
                                {plan[currentSemester].goals.map((goal, index) => (
                                    <li key={index}>{goal}</li>
                                ))}
                            </ul>
                        </div>
                        <div className="controls">
                            <button onClick={prevSemester}>Previous</button>
                            <span>{currentSemester + 1} / {plan.length}</span>
                            <button onClick={nextSemester}>Next</button>
                        </div>
                    </div>
                ) : (
                    <p>Loading plan or no goals available.</p>
                )}
            </main>
        </div>
    )
}

function App() {
    return (
        <Routes>
            <Route path="/" element={<GoalsPage />} />
            <Route path="/plan" element={<PlanPage />} />
        </Routes>
    )
}

export default App
