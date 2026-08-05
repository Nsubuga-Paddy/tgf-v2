import { useNavigate } from 'react-router-dom'
import { useMember } from '../context/MemberContext'
import { formatUGX } from '../utils/format'
import ProjectIcon from './ProjectIcon'

export default function MyProjects() {
  const navigate = useNavigate()
  const { myProjects, addToast } = useMember()

  const openProject = (project) => {
    if (project.id === '52wsc') {
      navigate('/projects/52wsc')
      return
    }
    if (project.id === 'gwc') {
      navigate('/projects/gwc')
      return
    }
    if (project.id === 'cgf') {
      navigate('/projects/cgf')
      return
    }
    if (project.id === 'rep' || String(project.id).startsWith('rep-')) {
      const match = String(project.id).match(/^rep-(\d+)$/)
      if (match) {
        navigate(`/projects/rep/${match[1]}`)
        return
      }
      navigate('/projects/rep')
      return
    }
    addToast(`${project.name} is still under development`)
  }

  return (
    <section className="section" id="projects">
      <div className="section-head">
        <div>
          <h2>My projects</h2>
          <p className="section-note">Only initiatives you belong to · Open a project to contribute</p>
        </div>
        <span className="count">{myProjects.length}</span>
      </div>

      <div className="project-list">
        {myProjects.map((project) => (
          <article key={project.id} className="pcard">
            <div className="pcard-body">
              <div className="pcard-top">
                <div className="pcard-icon">
                  <ProjectIcon name={project.icon} />
                </div>
                <div className="pcard-titles">
                  <b>{project.name}</b>
                  <span>{project.cycleLine}</span>
                </div>
                <span className={`status-tag ${project.statusClass || 'st-active'}`}>
                  {project.status}
                </span>
              </div>

              <div className="pcard-amount">
                <small>Your position</small>
                {formatUGX(project.invested)}
              </div>

              <div className="pcard-stats">
                {project.stats.map((stat) => (
                  <div key={stat.label} className="s">
                    <div className="k">{stat.label}</div>
                    <div className="v">{stat.value}</div>
                  </div>
                ))}
              </div>

              <div className="cycle-bar">
                <div className="track">
                  <div className="fill" style={{ width: `${project.progress}%` }} />
                </div>
                <div className="cap">
                  <span>Cycle progress</span>
                  <span>{project.progress}%</span>
                </div>
              </div>
            </div>

            <div className="pcard-foot">
              <button type="button" className="btn btn-primary" onClick={() => openProject(project)}>
                Open
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
