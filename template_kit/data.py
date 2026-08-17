# -*- coding: utf-8 -*-
# ============================================================
# DATA — THIS is the file you edit every time with NEW CONTENT.
# (generate.py / build.py / config.py stay untouched — that's
#  what keeps every PDF visually identical.)
#
# ------------------------------------------------------------
# FLEXIBLE / STRUCTURE-AGNOSTIC SCHEMA
# ------------------------------------------------------------
# Each unit/chapter is a dict:
#
# {
#   "num": 11,                 # unit/chapter number (int or string)
#   "title": "Unit Title Here",
#   "blocks": [ ... ]          # <-- ORDERED LIST of content blocks.
# }
#
# "blocks" is where the flexibility comes from. Add ONLY the block
# types a given PDF actually has, IN WHATEVER ORDER you want them
# to appear. Every unit can have a totally different mix — some
# units might skip glossary, some might have two long-answer
# questions, some might have extra custom sections. Nothing else
# in the code needs to change.
#
# Supported block "type" values:
#
#   1) "notes"  — deep-dive / detailed notes
#      { "type": "notes", "label": "Deep-Dive Notes" (optional),
#        "sections": [
#           { "heading": "1. Heading",
#             "paras": [...],            # optional
#             "bullets": [...],          # optional
#             "numbered": [...],         # optional
#             "subsections": [           # optional
#                { "sub": "1.1 Sub-heading",
#                  "paras": [...], "bullets": [...], "numbered": [...] }
#             ]
#           }, ...
#        ]
#      }
#
#   2) "summary" — quick revision / key points box
#      { "type": "summary", "label": "Quick-Hit Revision — Key Points",
#        "points": ["Point 1", "Point 2", ...] }
#
#   3) "glossary" — key term definitions
#      { "type": "glossary", "label": "Key Glossary Terms",
#        "terms": [("Term", "Definition text..."), ...] }
#
#   4) "mcq" — multiple choice questions
#      { "type": "mcq", "label": "Multiple Choice Questions",
#        "items": [("Question?", ["OptA","OptB","OptC","OptD"], "B"), ...] }
#      (correct answer = the letter "A"/"B"/"C"/"D"...)
#
#   5) "short_qa" — short answer questions
#      { "type": "short_qa", "label": "Short Answer Questions",
#        "items": [("Question?", "Answer text..."), ...] }
#
#   6) "long_qa" — long answer question(s) — supports 1 or many
#      { "type": "long_qa", "label": "Long Answer Question",
#        "items": [
#           { "q": "Question text?",
#             "intro": "Opening paragraph...",
#             "extra_para_heading": "Optional mini heading",   # optional
#             "extra_para": "Optional paragraph",               # optional
#             "extra_para_heading2": "Optional 2nd mini heading", # optional
#             "extra_para2": "Optional paragraph",               # optional
#             "numbered_heading": "Optional heading before list", # optional
#             "numbered": ["<b>Point:</b> text", ...],           # optional
#             "outro": "Closing paragraph (renders in italics)."
#           }, ...
#        ]
#      }
#
#   7) "custom" — anything that doesn't fit the above (case studies,
#      formulas, extra reading, appendix, etc.) — same shape as "notes"
#      but with your own label.
#      { "type": "custom", "label": "Case Studies",
#        "sections": [ ... same shape as notes sections ... ] }
#
#   8) "table" — any tabular data (comparison tables, spec sheets, etc.)
#      { "type": "table", "label": "Optional Table Title",
#        "headers": ["Col 1", "Col 2", "Col 3"],
#        "rows": [
#           ["cell", "cell", "cell"],
#           ["cell", "<b>bold cell</b>", "cell"],   # <b> allowed in cells
#           ...
#        ]
#      }
#      TIP: "glossary" blocks can ALSO render as a table instead of a
#      list — just add "layout": "table" to a glossary block:
#      { "type": "glossary", "layout": "table", "terms": [...] }
#
#   9) "image" — diagrams/figures from the source PDF (one or several
#      side-by-side). Save the image files into the assets/ folder first.
#      { "type": "image", "label": "Optional Figure Title",
#        "items": [
#           {"src": "assets/my_diagram.png", "caption": "Fig 1: ...",
#            "width": "72mm"},   # width optional, default "150mm"
#           ...
#        ]
#      }
#
# NOTES:
#  - HTML tags like <b>...</b> ARE allowed inside text (bold key terms).
#  - Smart quotes: use \u201c \u201d \u2013 \u2014 or plain " - if unsure.
#  - "label" is optional on every block — if omitted, a sensible default
#    is used (see DEFAULT_LABELS in generate.py).
#  - Append unit dicts to UNITS in the order you want them printed.
#  - The 4 units below are a FULLY WORKING real example — copy the
#    pattern, replace the content, mix/reorder blocks however the
#    new PDF is actually structured.
# ============================================================

UNITS = []

# ---------------- UNIT 11 ----------------
unit11 = {
    "num": 11,
    "title": "Software Development, Design and Testing",
    "blocks": [
        {
            "type": "notes",
            "sections": [
                {
                    "heading": "1. Introduction to Software Development",
                    "paras": [
                        "Software is the engine that drives modern business decisions, scientific investigations, and engineering problem-solving. It is embedded in everything from telecommunications to medical systems.",
                        "Software development is the process of change, refinement, and transformation used to build application programs and their associated documents and data."
                    ]
                },
                {
                    "heading": "2. The Software Development Life Cycle (SDLC)",
                    "paras": ["The development of software is often viewed as a spiral or a series of methodical steps:"],
                    "subsections": [
                        {
                            "sub": "2.1 Analysis and Design",
                            "bullets": [
                                "<b>Requirements Analysis:</b> Defining the role of the software, including its function, behavior, performance, and constraints.",
                                "<b>Software Design:</b> A methodical approach using notations and guidelines to create a blueprint of the system."
                            ]
                        },
                        {
                            "sub": "2.2 Coding",
                            "paras": ["The process of translating the design into a programming language. Software engineers use different methods to write this code:"],
                            "bullets": [
                                "<b>Structured Programming:</b> A technique that uses a top-down approach and breaks programs into smaller, logical modules.",
                                "<b>Object-Oriented Programming (OOP):</b> Focuses on \u201cobjects\u201d rather than just functions, making code more reusable and scalable."
                            ]
                        },
                        {
                            "sub": "2.3 Software Testing",
                            "paras": ["Testing is critical to ensure the product meets the validation criteria and is free of major bugs. It establishes whether the software performs as intended within the defined constraints."]
                        }
                    ]
                },
                {
                    "heading": "3. Software Paradigms",
                    "paras": ["A software paradigm refers to the style or \u201cway\u201d of programming. Common paradigms include:"],
                    "bullets": [
                        "<b>Linear Sequential Model:</b> Also known as the Waterfall model, where one stage must be completed before the next begins.",
                        "<b>Iterative Models:</b> Where development happens in small, repeating cycles (like the Spiral model)."
                    ]
                },
                {
                    "heading": "4. Software Applications",
                    "paras": ["Software can be categorized into several functional areas:"],
                    "numbered": [
                        "<b>System Software:</b> Programs that manage the computer itself (e.g., OS).",
                        "<b>Real-time Software:</b> Software that must process data and respond instantly (e.g., air traffic control).",
                        "<b>Business Software:</b> Tools for payroll, inventory, and decision-making.",
                        "<b>Engineering/Scientific Software:</b> Used for complex simulations and calculations.",
                        "<b>Embedded Software:</b> Resides inside consumer products (e.g., washing machines, cars)."
                    ]
                }
            ]
        },
        {
            "type": "summary",
            "points": [
                "Software development is a continuous process of refinement and addition.",
                "Requirements Analysis defines what the software must do; Design defines how it will be built.",
                "Coding is the actual building phase using structured or object-oriented methods.",
                "Software Testing validates the product against the initial requirements.",
                "SDLC models (like the spiral) provide a methodical framework for engineers to follow.",
                "Software is categorized by its application, ranging from Real-time to Embedded systems."
            ]
        },
        {
            "type": "glossary",
            "terms": [
                ("SDLC", "Software Development Life Cycle — the spiral/methodical sequence of analysis, design, coding, and testing stages used to build software."),
                ("Requirements Analysis", "The stage where a software's function, behavior, performance, and constraints are defined."),
                ("Structured Programming", "A top-down coding technique that breaks a program into smaller, logical modules."),
                ("OOP", "Object-Oriented Programming — a paradigm that focuses on \u201cobjects\u201d to make code more reusable and scalable."),
                ("Waterfall Model", "A linear sequential SDLC model where each stage must be completed before the next begins."),
                ("Embedded Software", "Software that resides inside consumer products such as washing machines or cars.")
            ]
        },
        {
            "type": "mcq",
            "items": [
                ("Software engineering process is often viewed as a:", ["Circle","Spiral","Straight line","Square"], "B"),
                ("Which phase defines the function and performance of the software?", ["Coding","Design","Requirements Analysis","Testing"], "C"),
                ("A methodical approach to software blueprinting is called:", ["Coding","Software Design","Marketing","Troubleshooting"], "B"),
                ("Which programming method uses a top-down approach and logical modules?", ["OOP","Structured Programming","Random Coding","Machine Language"], "B"),
                ("Object-Oriented Programming (OOP) focuses primarily on:", ["Math","Functions","Objects","Hardware"], "C"),
                ("The phase where the design is translated into a programming language is:", ["Analysis","Testing","Coding","Deployment"], "C"),
                ("What ensures that the software meets its validation criteria?", ["Formatting","Testing","Sorting","Compiling"], "B"),
                ("Software that resides inside a car or microwave is _____ software.", ["System","Business","Embedded","Real-time"], "C"),
                ("Which software must process data and respond in milliseconds?", ["Business","Real-time","Educational","Entertainment"], "B"),
                ("Development itself is a process of refinement and _____:", ["Destruction","Change","Stagnation","Deletion"], "B"),
                ("Notations and guidelines for design are part of _____ methods.", ["Random","Structured","Manual","Social"], "B"),
                ("System engineering defines the _____ of software in a larger system.", ["Price","Role","Color","Location"], "B"),
                ("Which application category includes payroll and inventory systems?", ["Scientific","Business","Real-time","System"], "B"),
                ("Validation criteria are established during the _____ phase.", ["Coding","Analysis","Marketing","Maintenance"], "B"),
                ("Software is essentially a set of _____ programs.", ["Hardware","Application","Physical","Mechanical"], "B"),
                ("The \u201cstyle\u201d of programming followed by a team is its _____:", ["Algorithm","Paradigm","Logic","Sequence"], "B"),
                ("Which software category allows engineers to solve scientific problems?", ["Real-time","Business","Engineering/Scientific","Games"], "C"),
                ("Testing verifies software behavior against established _____:", ["Budgets","Constraints","Colors","Fonts"], "B"),
                ("Programming methods like Structured and OOP are used during:", ["Testing","Analysis","Coding","Installation"], "C"),
                ("Software is inescapable in the _____ century world.", ["18th","19th","20th","21st"], "D"),
            ]
        },
        {
            "type": "short_qa",
            "items": [
                ("Define Software Development.", "Software development is a methodical process of building software products. It involves change, refinement, transformation, and addition to existing products to solve computational tasks or meet specific business needs."),
                ("What happens during Requirements Analysis?", "During this phase, software engineers establish the information domain, functions, expected behavior, performance requirements, constraints, and validation criteria that the final software must meet."),
                ("What is Structured Programming?", "Structured programming is a methodical approach to coding that emphasizes breaking a large program into smaller, manageable, and logical modules. It uses a top-down design to make the code easier to read and maintain."),
                ("Explain the importance of Software Testing.", "Software testing is essential to ensure that the final product is reliable and performs exactly as specified during the analysis phase. It helps identify errors or \u201cbugs\u201d so they can be fixed before the software is released to users."),
                ("List three categories of software applications.", "(1) System Software (manages hardware); (2) Real-time Software (monitors/controls events as they occur); (3) Business Software (manages commercial data like payroll)."),
            ]
        },
        {
            "type": "long_qa",
            "items": [
                {
                    "q": "Explain the Software Development Life Cycle (SDLC) as a \u201cSpiral\u201d process and the significance of each stage.",
                    "intro": "The software engineering process is often viewed as a spiral, suggesting that development is not a one-time event but a continuous cycle of improvement.",
                    "numbered": [
                        "<b>System/Information Engineering:</b> The outermost layer where the broad role of the software within a larger system is defined.",
                        "<b>Software Requirements Analysis:</b> The stage where the \u201cwhat\u201d is defined. Engineers gather all necessary functional and performance requirements and establish how the software will be validated.",
                        "<b>Software Design:</b> The \u201chow\u201d stage. Engineers create technical blueprints, defining the data structures, architecture, and interface design using structured notations.",
                        "<b>Coding:</b> The construction phase. Using methods like Structured Programming or Object-Oriented Programming, the design is turned into executable instructions.",
                        "<b>Testing:</b> The validation phase. The code is put through various scenarios to ensure it meets the requirements and handles constraints correctly without crashing."
                    ],
                    "outro": "This spiral approach allows for constant feedback and refinement, ensuring that the final software product is robust, efficient, and perfectly aligned with the user's needs."
                }
            ]
        }
    ]
}
UNITS.append(unit11)

# ---------------- UNIT 12 ----------------
unit12 = {
    "num": 12,
    "title": "Operating System Concepts",
    "blocks": [
        {
            "type": "notes",
            "sections": [
                {
                    "heading": "1. Introduction to Operating Systems",
                    "paras": [
                        "An Operating System (OS) is a program that acts as an intermediary between a user of a computer and the computer hardware. It controls the execution of application programs and manages the system's hardware and software resources."
                    ]
                },
                {
                    "heading": "2. Goals and Functions of an OS",
                    "paras": ["The primary goals of an OS are to make the computer system convenient to use, manage resources efficiently, and provide an environment for running software."],
                    "subsections": [
                        {
                            "sub": "2.1 Major Functions",
                            "bullets": [
                                "<b>Process Management:</b> Managing the various programs (processes) that are currently running.",
                                "<b>Memory Management:</b> Tracking which parts of memory are in use and by whom.",
                                "<b>File Management:</b> Organizing data into files and folders for easy storage and retrieval.",
                                "<b>I/O Device Management:</b> Coordinating the use of peripherals like printers, monitors, and keyboards.",
                                "<b>Security:</b> Protecting data and programs from unauthorized access."
                            ]
                        },
                        {
                            "sub": "2.2 The OS as a Resource Manager",
                            "paras": ["The OS manages \u201cactive agents\u201d (processes) and \u201cpassive entities\u201d (resources). It ensures that multiple processes can share resources like the CPU and RAM without interfering with one another."]
                        }
                    ]
                },
                {
                    "heading": "3. Development and Evolution of Operating Systems",
                    "paras": ["The OS has evolved significantly to maximize hardware efficiency:"],
                    "bullets": [
                        "<b>Early Systems:</b> One user at a time with total control over the machine.",
                        "<b>Simple Batch Systems:</b> Jobs were grouped (batched) together to reduce setup time between programs.",
                        "<b>Multi-programmed Batch Systems:</b> Organizes jobs so the CPU always has something to execute, increasing CPU utilization.",
                        "<b>Time-Sharing Systems:</b> Allows multiple users to interact with the computer simultaneously by rapidly switching the CPU between them.",
                        "<b>Distributed Systems:</b> Distributes computation among several physical processors to increase speed and reliability.",
                        "<b>Real-time (RT) Systems:</b> Used when there are rigid time requirements on the operation of a processor (e.g., medical imaging or industrial control)."
                    ]
                },
                {
                    "heading": "4. Operating System Services",
                    "paras": ["An OS provides an environment for the execution of programs and services to the users:"],
                    "numbered": [
                        "<b>Program Execution:</b> Loading a program into memory and running it.",
                        "<b>I/O Operations:</b> Managing communication with devices.",
                        "<b>File-System Manipulation:</b> Reading, writing, and deleting files.",
                        "<b>Communication:</b> Exchanging information between processes on the same or different computers.",
                        "<b>Error Detection:</b> Constantly monitoring for hardware or software errors."
                    ]
                }
            ]
        },
        {
            "type": "summary",
            "points": [
                "An OS is the interface between the user/applications and the computer hardware.",
                "Multi-programming ensures the CPU stays busy by keeping multiple jobs in memory.",
                "Time-sharing provides a fast response time for multiple interactive users.",
                "Real-time systems are essential for applications where timing is critical.",
                "The OS manages both Resources (hardware) and Services (user functions).",
                "Components of an OS include the kernel, shell, and file system."
            ]
        },
        {
            "type": "glossary",
            "layout": "table",
            "terms": [
                ("Kernel", "The core component of an OS that is always resident in RAM and manages system resources."),
                ("Multi-programming", "A technique where multiple jobs are kept in main memory simultaneously so the CPU always has something to execute."),
                ("Time-Sharing", "An extension of multi-programming that lets many users interact with a computer at once via rapid CPU switching."),
                ("Process", "A program in execution, treated as an active agent that competes for system resources."),
                ("Distributed System", "A system that distributes computation among several physical processors to increase speed and reliability.")
            ]
        },
        {
            "type": "mcq",
            "items": [
                ("Which of the following acts as an interface between user and hardware?", ["Compiler","Operating System","RAM","Browser"], "B"),
                ("The goal of Multi-programming is to increase:", ["Speed","CPU Utilization","Storage","User count"], "B"),
                ("A program in execution is called a:", ["File","Resource","Process","Command"], "C"),
                ("Which OS type is designed for immediate response in industrial control?", ["Batch","Distributed","Real-time","Time-sharing"], "C"),
                ("Time-sharing is an extension of _____ systems.", ["Batch","Multi-programmed","Single-user","Manual"], "B"),
                ("The OS function that handles storage of data on a disk is:", ["Process Management","File Management","I/O Management","Security"], "B"),
                ("In a Distributed System, computation is shared among several _____:", ["Users","Keyboards","Processors","Monitors"], "C"),
                ("Which service allows two programs to exchange information?", ["Error detection","Communication","File system","I/O operations"], "B"),
                ("Early systems used _____ to reduce setup time between jobs.", ["Chips","Batching","Internet","GUI"], "B"),
                ("The OS component that is always resident in RAM is the:", ["Shell","User Profile","Kernel","Application"], "C"),
                ("Which of the following is NOT a major goal of an OS?", ["Efficiency","Convenience","Hardware design","Resource management"], "C"),
                ("Device management is primarily about coordinating:", ["Files","Sub-folders","Peripherals","Users"], "C"),
                ("What happens to the CPU in a multi-programming system if the current job waits for I/O?", ["It stops","It reboots","It switches to another job","It waits"], "C"),
                ("Distributed systems are designed to increase speed and _____:", ["Heat","Reliability","Complexity","Cost"], "B"),
                ("Which OS service allows a user to create and delete directories?", ["Program execution","I/O Operations","File-system manipulation","Resource allocation"], "C"),
                ("Operating systems for \u201cEmbedded\u201d computers are found in:", ["Supercomputers","Household appliances","Mainframes","Servers"], "B"),
                ("Which term describes entities like the CPU, memory, and I/O devices?", ["Active agents","Passive entities/Resources","Software","Procedures"], "B"),
                ("The interface through which a user interacts with the OS is often the:", ["ALU","Shell/GUI","Hard Drive","Bus"], "B"),
                ("An OS service that monitors for system malfunctions is:", ["Resource allocation","Error detection","Accounting","Protection"], "B"),
                ("Servers and Workstations require different _____ of Operating Systems.", ["Hardware","Colors","Flavors/Types","Sizes"], "C"),
            ]
        },
        {
            "type": "short_qa",
            "items": [
                ("What is the definition of an Operating System?", "An Operating System (OS) is a specialized program that manages computer hardware and software resources and provides a common environment for computer programs to run. It acts as a bridge between the user/applications and the physical hardware."),
                ("Explain 'Multi-programming'.", "Multi-programming is a technique where multiple jobs are kept in the main memory simultaneously. If one job needs to wait for an I/O operation (like printing), the OS switches the CPU to another job. This ensures the CPU is utilized as much as possible."),
                ("What are 'Time-sharing' systems?", "Time-sharing is an evolution of multi-programming that allows many users to share the same computer at once. The OS switches the CPU between users so quickly that each user feels as if they have the entire machine to themselves."),
                ("Define a 'Real-time' Operating System.", "A Real-time (RT) OS is used when there are strict time constraints on processing. It is designed to guarantee a response within a specified time limit, making it crucial for things like flight control, medical equipment, or industrial robotics."),
                ("List three services provided by an OS.", "(1) Program Execution: Loading and running software; (2) File-system Manipulation: Creating, reading, and deleting files; (3) Error Detection: Identifying and responding to hardware or software faults."),
            ]
        },
        {
            "type": "long_qa",
            "items": [
                {
                    "q": "Discuss the role of the Operating System as a Resource Manager and explain the different types of resources it handles.",
                    "intro": "The Operating System acts as a \u201cResource Manager\u201d to ensure that the computer's hardware and software components are used efficiently and fairly by various competing programs.",
                    "extra_para_heading": "The Concept of Resource Management",
                    "extra_para": "The OS manages the relationship between Active Agents (processes or programs currently running) and Passive Entities (resources like memory and processors). Without a manager, two programs might try to use the same piece of memory at the same time, leading to a system crash.",
                    "numbered_heading": "Types of Resources Managed",
                    "numbered": [
                        "<b>CPU (Processor):</b> The OS determines which process gets the \u201cattention\u201d of the CPU and for how long. In multi-tasking, it switches between processes thousands of times per second.",
                        "<b>Memory (RAM):</b> The OS allocates specific \u201cblocks\u201d of memory to each program. It ensures that no program accesses memory it doesn't own, protecting the system's stability.",
                        "<b>I/O Devices:</b> Peripherals like printers or keyboards are shared resources. The OS manages the queue of requests to these devices so that data isn't mixed up or lost.",
                        "<b>Storage (File System):</b> The OS manages how data is laid out on the hard drive, controlling access rights so users can only see or edit their own files."
                    ],
                    "outro": "By serving as a centralized manager, the OS prevents resource conflicts, optimizes system performance, and provides a stable, secure environment for the user."
                }
            ]
        }
    ]
}
UNITS.append(unit12)

# ---------------- UNIT 13 ----------------
unit13 = {
    "num": 13,
    "title": "Communication System Concepts",
    "blocks": [
        {
            "type": "notes",
            "sections": [
                {
                    "heading": "1. Introduction to Communication Systems",
                    "paras": ["A communication system is a collection of hardware and software designed to transmit information from one point to another. In the digital age, this involves computer networks that allow devices to exchange data using specific protocols and transmission media."]
                },
                {
                    "heading": "2. Basic Elements of Communication",
                    "paras": ["Every communication system consists of five essential components:"],
                    "numbered": [
                        "<b>Message:</b> The information (data) to be communicated.",
                        "<b>Sender:</b> The device that sends the data message (e.g., computer, workstation).",
                        "<b>Receiver:</b> The device that receives the message.",
                        "<b>Transmission Medium:</b> The physical path by which a message travels from sender to receiver.",
                        "<b>Protocol:</b> A set of rules that governs data communication."
                    ]
                },
                {
                    "heading": "3. Data Communication Concepts",
                    "subsections": [
                        {
                            "sub": "3.1 Transmission Media",
                            "paras": ["The physical path between transmitter and receiver can be:"],
                            "bullets": [
                                "<b>Guided Media (Wired):</b> Uses physical cables like Twisted-pair, Coaxial cable, or Fiber-optics.",
                                "<b>Unguided Media (Wireless):</b> Uses electromagnetic waves to transmit data through the air (e.g., Radio waves, Microwaves, Infrared)."
                            ]
                        },
                        {
                            "sub": "3.2 Network Topologies",
                            "paras": ["Topology refers to the geometric arrangement of devices in a network:"],
                            "bullets": [
                                "<b>Mesh:</b> Every device has a dedicated point-to-point link to every other device.",
                                "<b>Star:</b> Each device has a dedicated link only to a central controller (Hub/Switch).",
                                "<b>Bus:</b> One long cable acts as a backbone to link all devices.",
                                "<b>Ring:</b> Each device has a dedicated point-to-point connection with only the two devices on either side of it."
                            ]
                        }
                    ]
                },
                {
                    "heading": "4. Network Types",
                    "paras": ["Computer networks are categorized based on their scope and scale:"],
                    "bullets": [
                        "<b>LAN (Local Area Network):</b> Connects devices in a small area like a home or office.",
                        "<b>MAN (Metropolitan Area Network):</b> Connects a larger area, such as a city.",
                        "<b>WAN (Wide Area Network):</b> Provides long-distance transmission over countries or continents (e.g., the Internet)."
                    ]
                },
                {
                    "heading": "5. Network Models (OSI and TCP/IP)",
                    "subsections": [
                        {
                            "sub": "5.1 OSI Reference Model",
                            "paras": ["The Open Systems Interconnection (OSI) model is a theoretical framework with seven layers: Physical | Data Link | Network | Transport | Session | Presentation | Application."]
                        },
                        {
                            "sub": "5.2 TCP/IP Model",
                            "paras": ["The Transmission Control Protocol/Internet Protocol model is the practical suite used for the modern Internet. It consists of four layers: Network Access, Internet, Transport, and Application."]
                        }
                    ]
                },
                {
                    "heading": "6. Internet Components",
                    "bullets": [
                        "<b>WWW (World Wide Web):</b> A system of interlinked hypertext documents accessed via the Internet.",
                        "<b>Web Browser:</b> Software used to access the web (e.g., Chrome, Firefox).",
                        "<b>Web Server:</b> A computer that stores and delivers web pages to users.",
                        "<b>HTTP:</b> The protocol used for transmitting web pages.",
                        "<b>IP Addressing:</b> A unique numerical label assigned to each device connected to a network."
                    ]
                }
            ]
        },
        {
            # DEMO: "image" block — used for diagrams/figures from the source PDF.
            # "items" is a list so you can place several related diagrams side by side.
            "type": "image",
            "label": "Network Topology Diagrams",
            "items": [
                {"src": "assets/diagram_star_topology.png", "caption": "Star Topology", "width": "72mm"},
                {"src": "assets/diagram_ring_topology.png", "caption": "Ring Topology", "width": "72mm"},
            ]
        },
        {
            # DEMO: "table" block — used for any tabular data/comparison from the source PDF.
            "type": "table",
            "label": "Guided vs Unguided Media \u2014 Comparison",
            "headers": ["Aspect", "Guided Media (Wired)", "Unguided Media (Wireless)"],
            "rows": [
                ["Signal path", "Physical cable (conductor)", "Through air/space, no physical conductor"],
                ["Examples", "Twisted-pair, Coaxial, Fiber-optic", "Radio waves, Microwaves, Infrared"],
                ["Typical use", "LANs, wired backbones", "Mobile networks, satellite links"],
                ["Installation cost", "Higher (cabling required)", "Lower (no cabling), but equipment can be costly"],
            ]
        },
        {
            "type": "summary",
            "points": [
                "Communication requires a Sender, Receiver, Medium, Message, and Protocol.",
                "Guided media uses cables; Unguided media uses wireless signals.",
                "Topologies (Star, Bus, Mesh, Ring) define how devices are physically connected.",
                "LAN, MAN, and WAN define the geographic scope of a network.",
                "The OSI model is a 7-layer standard for network communication.",
                "The Internet relies on TCP/IP protocols, IP addresses, and the World Wide Web."
            ]
        },
        {
            "type": "glossary",
            "terms": [
                ("Protocol", "A set of rules that governs how data communication takes place between devices."),
                ("Topology", "The geometric arrangement of devices in a network (e.g., Star, Bus, Mesh, Ring)."),
                ("OSI Model", "A theoretical 7-layer framework (Physical to Application) describing how network communication works."),
                ("TCP/IP Model", "The practical 4-layer protocol suite that actually runs the modern Internet."),
                ("IP Address", "A unique numerical label assigned to every device connected to a network.")
            ]
        },
        {
            "type": "mcq",
            "items": [
                ("The set of rules that governs data communication is called a:", ["Topology","Protocol","Medium","Message"], "B"),
                ("Which topology connects every device to a central hub?", ["Bus","Mesh","Star","Ring"], "C"),
                ("A network covering a city is called a:", ["LAN","MAN","WAN","PAN"], "B"),
                ("Fiber-optic cable is an example of _____ media.", ["Guided","Unguided","Satellite","Wireless"], "A"),
                ("How many layers are in the OSI model?", ["4","5","7","9"], "C"),
                ("The \u201cInternet\u201d is the most well-known example of a:", ["LAN","MAN","WAN","Intranet"], "C"),
                ("Which layer of the OSI model is responsible for routing data packets?", ["Physical","Data Link","Network","Application"], "C"),
                ("WWW stands for:", ["World Wide Web","Web Wide World","West Wide Web","Work Wide Web"], "A"),
                ("Which protocol is used to access web pages?", ["FTP","SMTP","HTTP","SNMP"], "C"),
                ("A unique numerical address for a computer on a network is an:", ["URL","IP Address","ISP","Mac Address"], "B"),
                ("In a _____ topology, all devices share a single communication line.", ["Star","Bus","Mesh","Ring"], "B"),
                ("The physical path between transmitter and receiver is the:", ["Protocol","Transmission Medium","Encoder","Decoder"], "B"),
                ("Which model is a 4-layer practical suite for the Internet?", ["OSI","TCP/IP","ISO","IEEE"], "B"),
                ("Radio waves are an example of _____ media.", ["Guided","Unguided","Twisted-pair","Coaxial"], "B"),
                ("Which layer is the topmost layer of the OSI model?", ["Physical","Transport","Session","Application"], "D"),
                ("Which device stores and delivers web pages to your browser?", ["Web Client","Web Server","Hub","Router"], "B"),
                ("A network within a single building is a:", ["LAN","MAN","WAN","GAN"], "A"),
                ("The _____ layer of the OSI model handles the mechanical and electrical specifications.", ["Application","Presentation","Physical","Network"], "C"),
                ("What is the protocol used for sending emails?", ["HTTP","SMTP","FTP","TCP"], "B"),
                ("Which network topology offers the highest reliability but is most expensive to install?", ["Bus","Star","Mesh","Ring"], "C"),
            ]
        },
        {
            "type": "short_qa",
            "items": [
                ("List the five basic elements of a communication system.", "(1) Message (the data); (2) Sender (source); (3) Receiver (destination); (4) Transmission Medium (the path); and (5) Protocol (the rules)."),
                ("Differentiate between Guided and Unguided Media.", "Guided Media provides a physical conduit (like wires/cables) to direct signals from sender to receiver. Unguided Media (Wireless) transmits electromagnetic waves through the air or water without a physical conductor."),
                ("Explain 'Star Topology'.", "In a Star topology, each network device is connected to a central controller called a hub or switch. All communication between devices must pass through the central hub, which acts as a signal repeater."),
                ("What is the purpose of the OSI model?", "The Open Systems Interconnection (OSI) model provides a standard framework for different computer systems to communicate with each other by breaking the complex process of networking into seven manageable layers."),
                ("Define an IP Address.", "An IP (Internet Protocol) address is a unique numerical label assigned to every device participating in a computer network. It serves two main functions: host or network interface identification and location addressing."),
            ]
        },
        {
            "type": "long_qa",
            "items": [
                {
                    "q": "Compare the OSI and TCP/IP models. Why is the TCP/IP model considered more practical for the modern Internet?",
                    "intro": "Both the OSI and TCP/IP models are used to describe how data is transmitted across a network, but they differ in structure and application.",
                    "extra_para_heading": "OSI Model",
                    "extra_para": "It is a 7-layer theoretical model (Physical, Data Link, Network, Transport, Session, Presentation, Application). It was designed to be a universal standard, but it is often criticized for being too complex, as some layers perform very similar tasks or have little practical use in modern networking.",
                    "extra_para_heading2": "TCP/IP Model",
                    "extra_para2": "It is a 4-layer functional model (Network Access, Internet, Transport, Application). It was developed alongside the Internet itself and focuses on the core protocols (TCP and IP) that make the web work.",
                    "numbered_heading": "Comparison and Practicality",
                    "numbered": [
                        "<b>Simplification:</b> TCP/IP combines the top three layers of the OSI model (Session, Presentation, Application) into a single \u201cApplication\u201d layer, making it more streamlined.",
                        "<b>Hardware Independence:</b> It combines the OSI Physical and Data Link layers into a \u201cNetwork Access\u201d layer, focusing more on how data is framed rather than the specific electrical hardware.",
                        "<b>Real-world Adoption:</b> TCP/IP is the actual set of protocols used on the Internet today."
                    ],
                    "outro": "In summary, the TCP/IP model is more practical because it reflects the actual evolution of the Internet, prioritizing functionality and simplicity over the theoretical strictness of the OSI model."
                }
            ]
        }
    ]
}
UNITS.append(unit13)

# ---------------- UNIT 14 ----------------
unit14 = {
    "num": 14,
    "title": "TCP/IP and Internet",
    "blocks": [
        {
            "type": "notes",
            "sections": [
                {
                    "heading": "1. Introduction to TCP/IP",
                    "paras": ["TCP/IP (Transmission Control Protocol/Internet Protocol) is the foundational protocol suite of the Internet. While the computer is an information tool, networks enhance its ability to exchange, preserve, and protect that information by allowing direct computer-to-computer communication without human intermediaries."]
                },
                {
                    "heading": "2. TCP/IP Architecture and Layers",
                    "paras": ["TCP/IP is modeled in layers, often referred to as a \u201cprotocol stack.\u201d It is designed for \u201cInternetworking\u201d\u2014connecting different types of networks into one cohesive system."],
                    "bullets": [
                        "<b>Application Layer:</b> The top layer where programs (like email or web browsers) create data.",
                        "<b>Transport Layer:</b> Ensures data is delivered reliably between hosts (using TCP or UDP).",
                        "<b>Internet Layer:</b> Handles the routing of data packets across the network using IP Addresses.",
                        "<b>Network Access Layer:</b> The bottom layer that manages the physical transmission of data over hardware."
                    ]
                },
                {
                    "heading": "3. How the Internet Works",
                    "paras": ["The Internet is a \u201cNetwork of Networks\u201d connected by high-speed communication lines called Backbones."],
                    "subsections": [
                        {
                            "sub": "3.1 Key Hardware Components",
                            "bullets": [
                                "<b>Server:</b> A powerful computer that stores and shares data with other computers (clients).",
                                "<b>Router:</b> A specialized device that acts as a traffic controller, directing \u201cpackets\u201d of data to their correct destination.",
                                "<b>Modem:</b> Short for Modulator/Demodulator; it converts digital signals from the computer into analog signals for transmission over phone/cable lines and vice-versa."
                            ]
                        },
                        {
                            "sub": "3.2 Internet Service Provider (ISP)",
                            "paras": ["An ISP is a company that provides you with access to the Internet for a periodic fee. They connect your local network to the global Internet backbone."]
                        }
                    ]
                },
                {
                    "heading": "4. Internet Applications and Tools",
                    "bullets": [
                        "<b>The World Wide Web (WWW):</b> A system of interlinked hypertext documents.",
                        "<b>Web Browser:</b> Software used to view web pages. Internet Explorer (by Microsoft) was a historically dominant browser.",
                        "<b>Electronic Mail (E-mail):</b> A system for sending and receiving messages. It uses Mailboxes to store incoming messages until the user reads them.",
                        "<b>Telnet:</b> A protocol that allows a user to log into a remote computer as if they were sitting at its keyboard."
                    ]
                }
            ]
        },
        {
            "type": "summary",
            "points": [
                "TCP/IP is a layered protocol suite that enables global internetworking.",
                "IP Addressing is essential for identifying every device on the network.",
                "Backbones are the high-capacity lines that carry the majority of Internet traffic.",
                "Routers direct data packets, while Modems translate signals between digital and analog.",
                "ISPs act as the gateway for users to access the Internet.",
                "Common applications include E-mail, WWW, and Telnet.",
                "Data on the Internet is broken down into small pieces called Packets for transmission."
            ]
        },
        {
            "type": "glossary",
            "terms": [
                ("Protocol Stack", "The layered representation of networking software (like TCP/IP), each layer handling a specific part of communication."),
                ("Router", "A device that acts as a traffic controller, directing data packets to their correct destination."),
                ("ISP", "Internet Service Provider — a company that connects a local network to the global Internet backbone."),
                ("Packet", "A small, manageable chunk of data (with sender/receiver IP addresses) that data is broken into for transmission."),
                ("Modem", "Modulator/Demodulator — converts digital signals to analog for transmission and back again.")
            ]
        },
        {
            "type": "mcq",
            "items": [
                ("Which protocol suite is the foundation of the modern Internet?", ["OSI","TCP/IP","HTTP","FTP"], "B"),
                ("The set of layers in a protocol suite is often called a:", ["Bundle","Stack","String","Cluster"], "B"),
                ("Which device converts digital signals to analog and vice-versa?", ["Router","Server","Modem","Switch"], "C"),
                ("A powerful computer that provides data to other computers is a:", ["Client","Server","Router","Packet"], "B"),
                ("Small pieces of data sent over the Internet are called:", ["Bits","Files","Packets","Layers"], "C"),
                ("Which device is a \u201cmultiport repeater\u201d?", ["Router","Hub","Modem","Server"], "B"),
                ("What does ISP stand for?", ["Internet System Protocol","Internet Service Provider","Internal Service Port","International Standard Path"], "B"),
                ("The high-speed lines that connect the Internet are called:", ["Backbones","Ribs","Spines","Cables"], "A"),
                ("Which protocol allows you to log into a remote computer?", ["HTTP","FTP","Telnet","SMTP"], "C"),
                ("Internet Explorer is an example of a:", ["Server","Web Browser","ISP","Search Engine"], "B"),
                ("In an email system, messages are stored in a:", ["Router","Mailbox","Address Bar","Modem"], "B"),
                ("The \u201cInternet\u201d began as a research project for which agency?", ["NASA","ARPA (Advanced Research Project Agency)","FBI","UN"], "B"),
                ("Fiber-optic cables transmit data using:", ["Electricity","Total Internal Reflection (Light)","Radio waves","Magnetism"], "B"),
                ("Which device determines the best path for data packets?", ["Modem","Router","Keyboard","Monitor"], "B"),
                ("Where do you type the URL in a web browser?", ["Status Bar","Task Pane","Address Bar","Menu"], "C"),
                ("Which layer of TCP/IP handles actual physical transmission?", ["Application","Transport","Internet","Network Access"], "D"),
                ("TCP stands for:", ["Total Control Protocol","Transmission Control Protocol","Transfer Center Port","Technical Code Program"], "B"),
                ("The Internet is often described as a \u201cNetwork of _____\u201d:", ["Humans","Networks","Modems","Servers"], "B"),
                ("Which protocol ensures reliable delivery of data?", ["IP","TCP","HTTP","DNS"], "B"),
                ("Is an IP address unique to every device on a network?", ["Yes","No"], "A"),
            ]
        },
        {
            "type": "short_qa",
            "items": [
                ("Define a Protocol Stack.", "A protocol stack refers to the layered representation of networking software (like TCP/IP). Each layer in the stack handles a specific part of the communication process, from high-level applications down to physical hardware transmission."),
                ("What is the role of a Router?", "A router is a specialized device that connects different networks. Its main job is to act as a traffic controller, examining the destination address of incoming data packets and determining the best path to send them toward their final destination."),
                ("Explain what an ISP does.", "An ISP (Internet Service Provider) is a company that provides individuals and businesses with access to the Internet. They maintain the infrastructure and servers necessary to connect your home or office network to the global Internet backbone."),
                ("What are 'Packets' in Internet communication?", "When data (like an email or a photo) is sent over the Internet, it is broken down into small, manageable chunks called packets. Each packet contains a part of the data along with the sender and receiver's IP addresses. They are reassembled into the original file at the destination."),
                ("How does a Modem work?", "A modem (Modulator/Demodulator) bridges the gap between digital and analog. It converts the digital data from your computer into analog signals that can travel over traditional telephone or cable lines (modulation) and converts incoming analog signals back into digital data (demodulation)."),
            ]
        },
        {
            "type": "long_qa",
            "items": [
                {
                    "q": "Describe the TCP/IP Architectural Model and explain the function of each of its four layers.",
                    "intro": "The TCP/IP model is a practical framework used to standardize how data is moved across the Internet. It consists of four distinct layers:",
                    "numbered": [
                        "<b>Application Layer:</b> This is the top layer that interacts directly with the user and software. It handles high-level protocols like HTTP (for web browsing), SMTP (for email), and FTP (for file transfers). It is responsible for formatting the data so that the destination application can understand it.",
                        "<b>Transport Layer:</b> This layer is responsible for end-to-end communication and error checking. It uses the Transmission Control Protocol (TCP) to ensure that data arrives intact and in the correct order. If a packet is lost, this layer requests a re-transmission.",
                        "<b>Internet Layer:</b> The primary goal of this layer is routing. It uses the Internet Protocol (IP) to attach the source and destination IP addresses to data packets. It ensures that packets can navigate through various routers across different networks to reach the correct destination.",
                        "<b>Network Access Layer:</b> This is the lowest layer, dealing with the physical aspects of the network. It defines how data is physically sent through the transmission media, such as coaxial cables, fiber optics, or wireless signals. It manages the hardware interface between the computer and the network medium."
                    ],
                    "outro": "By organizing communication into these layers, the TCP/IP model allows different types of hardware and software to communicate seamlessly across the globe."
                }
            ]
        }
    ]
}
UNITS.append(unit14)
