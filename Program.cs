
using AppProperties.Properties;
using System.Xml.Serialization;

class Program
{
    static void Main(string[] args)
    {
        XmlSerializer serializer = new XmlSerializer(typeof(Config));
        using (FileStream stream = File.OpenRead(Environment.CurrentDirectory + "\\Properties\\config.xml"))
        {
            Config config = (Config)serializer.Deserialize(stream);

            DatabaseConfig database = config.Databases.FirstOrDefault(d => d.Id == "db2");


            Console.WriteLine("Database name: " + database.Name);
            Console.WriteLine("Database server: " + database.Server);
            Console.WriteLine("Database user: " + database.User);
            Console.WriteLine("Database password: " + database.Password);

            Console.WriteLine("Email server: " + config.Email.Server);
            Console.WriteLine("Email port: " + config.Email.Port);
            Console.WriteLine("Email user: " + config.Email.User);
            Console.WriteLine("Email password: " + config.Email.Password);

            Console.WriteLine("Logging level: " + config.Logging.Level);
            Console.WriteLine("Logging enabled: " + config.Logging.Enabled);
            Console.WriteLine("Logging destination: " + config.Logging.Destination);
            Console.WriteLine("Logging file path: " + config.Logging.FilePath);
            Console.ReadLine();
        }
    }
}