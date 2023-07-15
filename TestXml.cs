using System.Xml;
using Org.XmlUnit.Builder;
using Org.XmlUnit.Diff;
using Org.XmlUnit.Xpath;

namespace ConsoleApp1;

public class MyTestClass
{
    public void Example()
    {
        XPathEngine xpathEngine = new XPathEngine();
        String xpathSelector = "/root/struct[child::int = '3']"; // This the xpath expression from the feature file
        String valueXml = "<int>3</int><boolean>false</boolean>"; // this is the value from the feature file without the parent node
        String responseXml = "<root>   <struct>   <int>3</int><boolean>   false</boolean>\n<other>22</other></struct></root>"; // this is the actual response

        List<XmlNode> responseNodes = xpathEngine.SelectNodes(xpathSelector, Input.From(responseXml).Build()).ToList();
        String parentNodeName = responseNodes[0].Name; // parent node name extracted from the response
        String expectedValueXml = String.Format("<{0}>{1}</{2}>", parentNodeName, valueXml, parentNodeName); // expected value with the parent node as a string

        List<XmlNode> valueNodes = xpathEngine.SelectNodes("/" + parentNodeName, Input.From(expectedValueXml).Build())
            .ToList();
        XmlNodeList children = valueNodes[0].ChildNodes;
        HashSet<String> nodeNames = new HashSet<string>();
        for (int i = 0; i < children.Count; i++)
        {
            nodeNames.Add(children.Item(i).Name);
        }
        
        // This node filter keeps only the children nodes that are in the expectedValueXml
        Predicate<XmlNode> nodeFilter = node => 
        {
            while (node.ParentNode != null && !parentNodeName.Equals(node.ParentNode.Name)) 
            {
                node = node.ParentNode;
            }
            return node.ParentNode == null || nodeNames.Contains(node.Name);
        };
        // Calculate the diff
        Diff myDiff = DiffBuilder.Compare(expectedValueXml)
            .WithTest(responseNodes[0])
            .CheckForSimilar()
            .IgnoreWhitespace()
            .WithNodeFilter(nodeFilter)
            .Build();
        Console.WriteLine(myDiff.HasDifferences());
        Console.WriteLine(myDiff.ToString());
    }
}