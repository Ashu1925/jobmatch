import { useState, type FormEvent } from "react";
import "./App.css";


type Job = {
  id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  apply_url: string;
};

type ResumeResult = {
  text: string;
  skills: string[];
};

type MatchResult = {
  match_score: number;
  matching_skills: string[];
  missing_skills: string[];
};


type MatchedJob = Job & MatchResult;


function App() {
  const [token, setToken] = useState<string | null>(() =>
    sessionStorage.getItem("jobmatch_token")
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authMode, setAuthMode] = useState<"login" | "register">(
    "login"
  );
  const [authLoading, setAuthLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("");
  const [jobs, setJobs] = useState<MatchedJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);


  async function loginWithCredentials(
    loginEmail: string,
    loginPassword: string
  ): Promise<string> {
    const body = new URLSearchParams({
      username: loginEmail,
      password: loginPassword,
    });

    const response = await fetch(
      "http://127.0.0.1:8000/api/auth/login",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body,
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Unable to sign in.");
    }

    return data.access_token;
  }


  async function submitAuthentication(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();
    setAuthLoading(true);
    setError("");

    try {
      if (authMode === "register") {
        const response = await fetch(
          "http://127.0.0.1:8000/api/auth/register",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ email, password }),
          }
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.detail || "Unable to create the account."
          );
        }
      }

      const accessToken = await loginWithCredentials(
        email,
        password
      );

      sessionStorage.setItem("jobmatch_token", accessToken);
      setToken(accessToken);
      setPassword("");
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Authentication failed."
      );
    } finally {
      setAuthLoading(false);
    }
  }


  function logout() {
    sessionStorage.removeItem("jobmatch_token");
    setToken(null);
    setJobs([]);
    setResumeFile(null);
    setError("");
  }


  async function matchJob(
    job: Job,
    resume: string
  ): Promise<MatchedJob> {
    const response = await fetch(
      "http://127.0.0.1:8000/api/match",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          resume_text: resume,
          job_description: job.description,
        }),
      }
    );

    if (!response.ok) {
      throw new Error("Could not calculate a job match.");
    }

    const match: MatchResult = await response.json();

    return {
      ...job,
      ...match,
    };
  }
  async function extractResume(file: File): Promise<ResumeResult> {
    const formData = new FormData();
    formData.append("resume", file);

    const response = await fetch(
      "http://127.0.0.1:8000/api/resume/extract",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      }
    );

    if (!response.ok) {
      const errorData = await response.json();

      throw new Error(
        errorData.detail || "Could not read the resume PDF."
      );
    }

    return response.json();
  }


  async function searchJobs(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!resumeFile) {
      setError("Please select your resume PDF.");
      return;
    }

    if (!token) {
      setError("Please sign in before searching for jobs.");
      return;
    }

    if (resumeFile.type !== "application/pdf") {
      setError("Only PDF resumes are accepted.");
      return;
    }

    if (resumeFile.size > 5 * 1024 * 1024) {
      setError("The resume PDF must be 5 MB or smaller.");
      return;
    }

    setLoading(true);
    setError("");
    setJobs([]);

    const parameters = new URLSearchParams({
      keyword,
      location,
    });

    try {
      const resumeResult = await extractResume(resumeFile);

      const jobsResponse = await fetch(
        `http://127.0.0.1:8000/api/jobs?${parameters}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!jobsResponse.ok) {
        throw new Error("The live job search is unavailable.");
      }

      const jobData: Job[] = await jobsResponse.json();

      const matchedJobs = await Promise.all(
        jobData.map((job) =>
          matchJob(job, resumeResult.text)
        )
      );

      matchedJobs.sort(
        (firstJob, secondJob) =>
          secondJob.match_score - firstJob.match_score
      );

      setJobs(matchedJobs);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to search jobs right now. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }


  if (!token) {
    return (
      <main className="auth-page">
        <section className="auth-card">
          <p className="eyebrow">JOBMATCH INDIA</p>
          <h1>
            {authMode === "login"
              ? "Welcome back"
              : "Create your account"}
          </h1>

          <p>
            Sign in to upload your resume and find matching jobs.
          </p>

          <form className="auth-form" onSubmit={submitAuthentication}>
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                required
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={8}
                maxLength={128}
                autoComplete={
                  authMode === "login"
                    ? "current-password"
                    : "new-password"
                }
                required
              />
            </label>

            <button type="submit" disabled={authLoading}>
              {authLoading
                ? "Please wait..."
                : authMode === "login"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>

          {error && <p className="message error">{error}</p>}

          <button
            className="auth-switch"
            type="button"
            onClick={() => {
              setAuthMode(
                authMode === "login" ? "register" : "login"
              );
              setError("");
            }}
          >
            {authMode === "login"
              ? "Create a new account"
              : "Already have an account? Sign in"}
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="page">
      <section className="hero">
        <button className="logout-button" onClick={logout}>
          Sign out
        </button>
        <p className="eyebrow">JOBMATCH INDIA</p>

        <h1>Find jobs that fit your skills</h1>

        <p className="subtitle">
          Add your resume and discover your strongest matches.
        </p>

        <form
          className="search-form"
          onSubmit={searchJobs}
        >
          <label className="resume-field">
            Resume PDF

            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event) => {
                const file = event.target.files?.[0] ?? null;

                setResumeFile(file);
                setError("");
              }}
              required
            />

            {resumeFile && (
              <span className="selected-file">
                Selected: {resumeFile.name}
              </span>
            )}
          </label>

          <label>
            Role or skill

            <input
              type="text"
              value={keyword}
              onChange={(event) =>
                setKeyword(event.target.value)
              }
              placeholder="React, Python, data analyst..."
              maxLength={100}
            />
          </label>

          <label>
            Location

            <input
              type="text"
              value={location}
              onChange={(event) =>
                setLocation(event.target.value)
              }
              placeholder="Pune, Bengaluru, remote..."
              maxLength={100}
            />
          </label>

          <button
            type="submit"
            disabled={loading}
          >
            {loading
              ? "Finding matches..."
              : "Find matching jobs"}
          </button>
        </form>
      </section>

      {error && (
        <p className="message error">
          {error}
        </p>
      )}

      <section className="results">
        <h2>
          {jobs.length > 0
            ? `${jobs.length} matching ${
                jobs.length === 1 ? "job" : "jobs"
              }`
            : "Search for your next opportunity"}
        </h2>

        <div className="job-list">
          {jobs.map((job) => (
            <article
              className="job-card"
              key={job.id}
            >
              <div className="job-content">
                <div className="job-heading">
                  <div>
                    <h3>{job.title}</h3>

                    <p className="company">
                      {job.company}
                    </p>

                    <p className="location">
                      {job.location}
                    </p>
                  </div>

                  <strong className="match-score">
                    {job.match_score}% match
                  </strong>
                </div>

                <p className="job-description">
                  {job.description}
                </p>

                <div className="skills">
                  <div>
                    <h4>Matching skills</h4>

                    <div className="skill-list">
                      {job.matching_skills.length > 0
                        ? job.matching_skills.map((skill) => (
                            <span
                              className="skill matched"
                              key={skill}
                            >
                              {skill}
                            </span>
                          ))
                        : (
                            <span className="muted">
                              No recognized matches
                            </span>
                          )}
                    </div>
                  </div>

                  <div>
                    <h4>Skills to develop</h4>

                    <div className="skill-list">
                      {job.missing_skills.length > 0
                        ? job.missing_skills.map((skill) => (
                            <span
                              className="skill missing"
                              key={skill}
                            >
                              {skill}
                            </span>
                          ))
                        : (
                            <span className="muted">
                              No recognized missing skills
                            </span>
                          )}
                    </div>
                  </div>
                </div>
              </div>

              <a
                href={job.apply_url}
                target="_blank"
                rel="noreferrer"
              >
                View job
              </a>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}


export default App;
