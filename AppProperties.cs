using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace AppProperties.Properties
{

    using System;
    using System.IO;
    using System.Xml.Serialization;

    [XmlRoot("config")]
    public class Config
    {
        [XmlElement("database")]
        public DatabaseConfig[] Databases { get; set; }

        [XmlElement("email")]
        public EmailConfig Email { get; set; }

        [XmlElement("logging")]
        public LoggingConfig Logging { get; set; }
    }

    public class DatabaseConfig
    {
        [XmlAttribute("id")]
        public string Id { get; set; }

        [XmlElement("name")]
        public string Name { get; set; }

        [XmlElement("server")]
        public string Server { get; set; }

        [XmlElement("user")]
        public string User { get; set; }

        [XmlElement("password")]
        public string Password { get; set; }
    }

    public class EmailConfig
    {
        [XmlElement("server")]
        public string Server { get; set; }

        [XmlElement("port")]
        public int Port { get; set; }

        [XmlElement("user")]
        public string User { get; set; }

        [XmlElement("password")]
        public string Password { get; set; }
    }

    public class LoggingConfig
    {
        [XmlElement("level")]
        public string Level { get; set; }

        [XmlElement("enabled")]
        public bool Enabled { get; set; }

        [XmlElement("destination")]
        public string Destination { get; set; }

        [XmlElement("file_path")]
        public string FilePath { get; set; }
    }
}
