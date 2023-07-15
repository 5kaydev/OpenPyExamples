using System.Text;
using System.Text.RegularExpressions;
using ConvertedTests.Helpers;
using ConvertedTests.StepDefinitions;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Org.XmlUnit.Xpath;

namespace ConsoleApp1
{
    public class MyTestClass
    {
        private Random random = new();
        private Dictionary<string, string> variables = new();

        public void TestAssertJson()
        {
            var helper = new Helper();
            Console.WriteLine(helper.ValidateJsonResponse("xabcg", "~contains(abc)"));
            Console.WriteLine(helper.ValidateJsonResponse("abc", "abc"));

            var json = @"{ ""field1"": ""value1"", ""date"":""2023-05-06T00:00:00""}";
            using (JsonReader jsonReader = new JsonTextReader(new StringReader(json)))
            {
                jsonReader.DateParseHandling = DateParseHandling.None;

                var response = JObject.Load(jsonReader);
                var result = response.SelectToken("date");
                var resultString = (string)result;
                Console.WriteLine(resultString);
            }
            // var response = JObject.Parse(json);
            // var result = response.SelectToken("date");
            // var resultString = (string)result;
            // Console.WriteLine(resultString);
        }

        public void ExampleXml()
        {
            var xpathEngine = new XPathEngine();
            var xpathSelector = "/root/struct[child::int = '3']"; // This the xpath expression from the feature file
            var
                valueXml =
                    "<int>3</int><boolean>false</boolean>"; // this is the value from the feature file without the parent node
            var responseXml =
                "<root>   <struct>   <int>3</int><int>5</int><boolean>  false</boolean><attr \n<other>22</other></struct></root>"; // this is the actual response
            var expectedXml = "<boolean>  false</boolean><int>3</int>";

            xpathSelector = "/MoatClientResponse/ExternalPolicies/ExternalPolicy[child::PolicyEffectiveDate = '']";
            responseXml =
                @"<MoatClientResponse xmlns:xsd=""http://www.w3.org/2001/XMLSchema"" xmlns:xsi=""http://www.w3.org/2001/XMLSchema-instance"">
                <ExternalPolicies>
                <ExternalPolicy>
                <ExternalPolicyId>-256239521</ExternalPolicyId>
                <ChangeType>None</ChangeType>
                <PolicyEffectiveDate xsi:nil=""true"" />
                <PolicyExpirationDate xsi:nil=""true"" />
                <PolicyStatus>CN</PolicyStatus>
                <PolicyIssueDate xsi:nil=""true"" />
                <PolicyCancellationDate xsi:nil=""true"" />
                <TechnicalObjectKey>TRH6444818279</TechnicalObjectKey>
                <TerminalId />
                <PlanCode>PHOD</PlanCode>
                <ObjectSystemId>PIC</ObjectSystemId>
                <LegacyCompanyCode />
                <SobCode xsi:nil=""true"" />
                <LastModifiedBy>TESTER</LastModifiedBy>
                </ExternalPolicy>
                </ExternalPolicies>
                </MoatClientResponse>";
            expectedXml = @"<TechnicalObjectKey>TRH6444818279</TechnicalObjectKey>
<PolicyEffectiveDate></PolicyEffectiveDate>
<PolicyExpirationDate></PolicyExpirationDate>
<PolicyStatus>CN</PolicyStatus>
<PolicyIssueDate></PolicyIssueDate>
<PlanCode>PHOD</PlanCode>
<TerminalId></TerminalId>
<LegacyCompanyCode></LegacyCompanyCode>";
            var helper = new Helper();

            Console.WriteLine(helper.ValidateXmlResponse(responseXml, xpathSelector, expectedXml));
            Console.WriteLine("End of XML test");
            // List<XmlNode> responseNodes = xpathEngine.SelectNodes(xpathSelector, Input.From(responseXml).Build()).ToList();
            // responseNodes[0].
            // String parentNodeName = responseNodes[0].Name; // parent node name extracted from the response
            // String expectedValueXml = valueXml.StartsWith("<"+parentNodeName) ? valueXml : $"<{parentNodeName}>{valueXml}</{parentNodeName}>"; // expected value with the parent node as a string
            //
            // List<XmlNode> valueNodes = xpathEngine.SelectNodes("/" + parentNodeName, Input.From(expectedValueXml).Build())
            //     .ToList();
            // XmlNodeList children = valueNodes[0].ChildNodes;
            // HashSet<String> nodeNames = new HashSet<string>();
            // for (int i = 0; i < children.Count; i++)
            // {
            //     nodeNames.Add(children.Item(i).Name);
            // }
            //
            // // This node filter keeps only the children nodes that are in the expectedValueXml
            // Predicate<XmlNode> nodeFilter = node =>
            // {
            //     Console.WriteLine("My node is "+ node.OuterXml);
            //     while (node.ParentNode != null && !parentNodeName.Equals(node.ParentNode.Name))
            //     {
            //         node = node.ParentNode;
            //     }
            //     return node.ParentNode == null || nodeNames.Contains(node.Name);
            // };
            // // Calculate the diff
            // Diff myDiff = DiffBuilder.Compare(expectedValueXml)
            //     .WithTest(responseNodes[0])
            //     .CheckForSimilar()
            //     .IgnoreWhitespace()
            //     .WithNodeFilter(nodeFilter)
            //     // .WithNodeMatcher(new DefaultNodeMatcher(ElementSelectors.ByName))
            //     .Build();
            // Console.WriteLine(myDiff.HasDifferences());
            // Console.WriteLine(myDiff.ToString());
        }

        public void Example()
        {
            var store = new VariableStore();
            store.StoreVariable("{variable}", "Hello World!");
            Console.WriteLine(store.Substitute("~substring ({variable}, 6, 5)"));
            Console.WriteLine(store.Substitute("<brol>~Random{aaBB99()[]}"));
            Console.WriteLine(store.Substitute("<bla>~randomize{15}</bla>"));
            Console.WriteLine(store.Substitute("<bla>~randomize{5,4}</bla>"));
            Console.WriteLine(store.Substitute("<bla>~randomize{0,10}</bla>"));
            Console.WriteLine(store.Substitute("<bla>#getDAte( 0 )</bla>"));
            Console.WriteLine(store.Substitute("<bla>#gettime(-45)</bla>"));
            // Console.WriteLine("getkey test");
            // Console.WriteLine(store.GenerateValue("NNNN-NN-NNTNN:NN:NN"));
            // Console.WriteLine(store.GenerateValue("N&gt;NNN-a&amp;aa-AAA-&lt;bcd"));
            // Console.WriteLine(store.Substitute("<bla>~getkey(brol,ANAN)</bla><brol>~today-3{yyyy-MM-dd}</brol><testbrol>{b&rol}</testbrol><bla2>~getkey(mon brol,NNNN)</bla2>"));
            // // Console.WriteLine(store.Substitute("<example>{b&rol}</example><example2>{mon brol}</example2>"));
            Console.WriteLine(store.Substitute("<example>~getkey(brol,ANAN)</example><example2>{bRol}</example2>"));
            // var test = "<bla>~concat[[\"Samu1\"&TEXT(NOW(),\"ddHHss\")+1]]</bla>";
            // Console.WriteLine(store.Substitute(test));
            //var re = @"text\(now\(\).*?""(.*?)""";
            // var re = @"~randomize{(\d+)(\s*,\s*(\d+))?[^}]*}";
            // var regex = new Regex(re, RegexOptions.IgnoreCase);
            // var m = regex.Match("<bla>~randomize{15,jhgjh}</bla>");
            // if (m.Success)
            // {
            //     Console.WriteLine(m.Groups.Count);
            //     Console.WriteLine("g1 = " + m.Groups[1].Value);
            //     // Console.WriteLine("g2 = "+m.Groups[2].Value);
            //     // Console.WriteLine("g3 = "+m.Groups[3].Value);
            //     // Console.WriteLine("g4 = "+m.Groups[4].Value);
            // }
        }

        public void TestRegExp()
        {
            var regexp = new Regex("({[^:{}]*?})");
            var testJson =
                "{\"AddressLine1\":\"8315 S SEELEY AVE\",\"AddressLine2\":\"variableName\",\"UnitType\":\"000\",\"UnitNumber\":\"0\"}";
            var match = regexp.Match(testJson);
            if (match.Success)
            {
                Console.WriteLine(match.Value);
            }
        }

        public void TestRead()
        {
            //AppDomain.CurrentDomain.BaseDirectory
            var path = "/Users/viseem/src/specflow/XLSX_to_Specflow_Feature_Output/Level1_XML.req";
            var map = ReadRequests(path);
            Console.WriteLine(map);
        }

        public Dictionary<string, string> ReadRequests(string path)
        {
            var lines = File.ReadAllLines(path).ToList();
            var map = new Dictionary<string, string>();
            string? key = null;
            var builder = new StringBuilder();
            foreach (var line in lines)
            {
                if (line.StartsWith("##KEY:"))
                {
                    if (key != null)
                    {
                        map[key] = builder.ToString().Trim();
                    }
                    builder = new StringBuilder();
                    key = line.Substring(6);
                }
                else
                {
                    builder.AppendLine(line);
                }
            }
            if (key != null)
            {
                map[key] = builder.ToString().Trim();
            }
            return map;
        }
    }

    // public void AssertXmlResponseValid(string responseXml, string xpathSelector, string expectedValue)
    // {
    //     var message = ValidateXmlResponse(responseXml, xpathSelector, expectedValue);
    //     if (!string.Empty.Equals(message))
    //     {
    //         Assert.Fail(message);
    //     }
    // }
}